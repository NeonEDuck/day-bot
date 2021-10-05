import discord
from discord.ext import commands, tasks
from discord_slash import cog_ext
from discord_slash.utils.manage_commands import create_option, create_choice
from discord_slash.utils.manage_components import create_select, create_select_option, create_actionrow
from discord_slash.context import SlashContext, ComponentContext
from discord_slash.model import SlashMessage
from typing import Optional, Union, List, Tuple, Dict, Set, Any
from datetime import datetime, timedelta
import asyncio
from utils import get_bit_positions, utc_plus
from variable import DATETIME_FORMAT
from data_manager import DataManager

class Vote(commands.Cog):
    """投票模組

    這是一個包含所有關於投票的指令、行程的模組。
    """
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot
        self.data_manager = DataManager('vote')
        self.vote_closer.start()

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild) -> None:
        """在離開伺服器時的處理

        在離開伺服器時，將伺服器所有投票從資料庫刪除。
        """
        for _, title in self.data_manager.keys(guild.id):
            self.data_manager.del_val(title, guild.id)

    @tasks.loop(minutes=1.0)
    async def vote_closer(self) -> None:
        """投票關閉行程

        每一分鐘進行一次檢查，如果有投票超過關閉時間，關閉其投票並更新所有對應投票表單。
        """
        for tags, title in self.data_manager.keys():
            vote_info: Dict[str, Any] = self.data_manager.get_val(title, tags)
            if vote_info['closed'] or vote_info['close_date'] == None:
                continue
            if utc_plus(8) >= datetime.strptime(vote_info['close_date'], DATETIME_FORMAT):
                vote_info['closed'] = True
                vote_info['forced'] = False
                self.data_manager.set_val(title, vote_info, tags)
                await self.vote_update(self.bot, title, tags[0])

    @vote_closer.before_loop
    async def before_vote_closer(self) -> None:
        """投票關閉行程預備

        安排行程在系統時間下一分鐘整開始。
        """
        await self.bot.wait_until_ready()
        await asyncio.sleep(( 60 - (datetime.now().second + datetime.now().microsecond/1_000_000) ) % 60)
    
    vote_add_kwargs = {
        'base': 'vote',
        'name': 'add',
        'description': '新增一個投票。',
        # 'base_default_permission': False,
        'options': [
            create_option(
                name='title',
                description='投票標題。',
                option_type=3,
                required=True
            ),
            create_option(
                name='options',
                description='投票選項，請使用「 | 」分開各個選項。(格式：選項A|選項B)',
                option_type=3,
                required=True
            ),
            create_option(
                name='close_date',
                description='投票關閉日期。(格式：YYYY/MM/DD HH:MM，預設為無限)',
                option_type=3,
                required=False
            ),
            create_option(
                name='max_votes',
                description='一人最多能投幾票。(預設為1)',
                option_type=4,
                required=False
            ),
            create_option(
                name='show_members',
                description='是否在投票選項上顯示成員的選擇。(預設為False)',
                option_type=5,
                required=False
            )
        ]
    }
    @cog_ext.cog_subcommand(**vote_add_kwargs)
    async def _vote_add(self, ctx: SlashContext, title: str, options: str,
                        close_date: Optional[str]=None, max_votes: int=1,
                        show_members: bool=False) -> None:
        """新增投票指令

        /vote add <title> <option> [close_date] [max_votes] [show_members]
        新增一個投票並公佈投票表單在聊天室裡。
        """
        title   = title.strip()
        options = options.strip()

        vote_info: Dict[str, Any] = self.data_manager.get_val(title, ctx.guild_id)

        if vote_info:
            raise ValueError('vote', f'投票「{title}」」已經存在！')
        else:
            if close_date:
                self.check_close_date(close_date.strip())

            if max_votes <= 0:
                raise ValueError('vote', 'max_votes必須為大於等於1的值。')

            vote_info = {
                'options': [x.strip() for x in options.split('|')],
                'close_date': close_date,
                'max_votes': max_votes,
                'show_members': show_members,
                'closed': False,
                'forced': False,
                'voted': {},
                'vote_msgs': []
            }

            vote_msg: SlashMessage = await ctx.send(embed=self.make_embed(title, vote_info), components=[self.make_select(title, vote_info)])
            vote_info['vote_msgs'].append(str(vote_msg.id))
            self.data_manager.set_val(title, vote_info, ctx.guild_id)

    vote_remove_kwargs = {
        'base': 'vote',
        'name': 'remove',
        'description': '刪除指定投票。',
        'options': [
            create_option(
                name='title',
                description='投票標題。',
                option_type=3,
                required=True
            )
        ]
    }
    @cog_ext.cog_subcommand(**vote_remove_kwargs)
    async def _vote_remove(self, ctx: SlashContext, title: str) -> None:
        """刪除投票指令

        /vote remove <title>
        刪除一個投票。
        """
        title = title.strip()

        vote_info: Dict[str, Any] = self.data_manager.get_val(title, ctx.guild_id)

        if vote_info:
            for msg_id in vote_info['vote_msgs']:
                try:
                    msg: discord.Message = await ctx.channel.fetch_message(msg_id)
                    await msg.delete()
                except:
                    pass

            self.data_manager.del_val(title, ctx.guild_id)
            await ctx.send(f'以成功將投票「{title}」刪除！', hidden=True)
        else:
            raise KeyError('vote', f'投票「{title}」並不存在！')

    vote_edit_kwargs = {
        'base': 'vote',
        'name': 'edit',
        'description': '編輯指定投票的設定。',
        'options': [
            create_option(
                name='title',
                description='投票標題。',
                option_type=3,
                required=True
            ),
            create_option(
                name='new_title',
                description='新投票標題。',
                option_type=3,
                required=False
            ),
            create_option(
                name='options',
                description='投票選項，請使用「 | 」分開各個選項，使用「:  」分開索引與名字。(格式：0:選項A|2:選項C)',
                option_type=3,
                required=False
            ),
            create_option(
                name='close_date',
                description='關閉日期。(格式：YYYY/MM/DD HH:MM)',
                option_type=3,
                required=False
            ),
            create_option(
                name='max_votes',
                description='一人最多能投幾票。',
                option_type=4,
                required=False
            ),
            create_option(
                name='show_members',
                description='是否在投票選項上顯示成員的選擇。',
                option_type=5,
                required=False
            )
        ]
    }
    @cog_ext.cog_subcommand(**vote_edit_kwargs)
    async def _vote_edit(self, ctx: SlashContext, title: str,
                         new_title: Optional[str]=None, options: Optional[str]=None,
                         close_date: Optional[str]=None, max_votes: Optional[int]=None,
                         show_members: Optional[bool]=None) -> None:
        """編輯投票指令

        /vote edit <title> [new_title] [options] [close_date] [max_votes] [show_members]
        編輯投票上的各種資訊。
        """
        title = title.strip()

        vote_info: Dict[str, Any] = self.data_manager.get_val(title, ctx.guild_id)

        if not vote_info:
            raise KeyError('vote', f'投票「{title}」並不存在！')
        else:
            if options is not None:
                # 編輯選項
                options = options.strip()
                try:
                    options_list: List[Tuple[int, str]] = sorted([(int(i), name) for i, name in [opt.split(':') for opt in options.split('|')]], key=lambda x: x[0])
                except Exception as ex:
                    raise ValueError('vote', 'options格式錯誤。(格式：0:選項A|2:選項C)')
                for i, name in options_list:
                    if i >= len(vote_info['options']):
                        vote_info['options'].append(name)
                    else:
                        vote_info['options'][i] = name

            if close_date is not None:
                # 編輯關閉日期
                vote_info['close_date'] = self.check_close_date(close_date.strip())

            if max_votes is not None:
                # 編輯一人最多可投票票數
                if max_votes > 0:
                    vote_info['max_votes'] = max_votes
                else:
                    raise ValueError('vote', 'max_votes必須為大於等於1的值。')

            if show_members is not None:
                # 編輯是否顯示成員的選擇
                vote_info['show_members'] = show_members

            if new_title is not None:
                # 編輯投票標題
                new_title = new_title.strip()
                if not new_title:
                    raise ValueError('vote', 'new_title不得為空值')
                if self.data_manager.get_val(new_title, ctx.guild_id):
                    raise ValueError('vote', f'投票「{new_title}」已經存在，無法取代！')
                self.data_manager.set_val(new_title, vote_info, ctx.guild_id)
                self.data_manager.del_val(title, ctx.guild_id)
                await self.vote_update(ctx, new_title, ctx.guild_id)
                await ctx.send(f'以成功編輯投票「{new_title}」！', hidden=True)
            else:
                self.data_manager.set_val(title, vote_info, ctx.guild_id)
                await self.vote_update(ctx, title, ctx.guild_id)
                await ctx.send(f'以成功編輯投票「{title}」！', hidden=True)

    vote_close_kwargs = {
        'base': 'vote',
        'name': 'close',
        'description': '關閉指定投票。',
        'options': [
            create_option(
                name='title',
                description='投票標題。',
                option_type=3,
                required=True
            )
        ]
    }
    @cog_ext.cog_subcommand(**vote_close_kwargs)
    async def _vote_close(self, ctx: SlashContext, title: str) -> None:
        """關閉投票指令

        /vote close <title>
        關閉一個投票。
        """
        title = title.strip()

        vote_info: Dict[str, Any] = self.data_manager.get_val(title, ctx.guild_id)

        if vote_info:
            vote_info['closed'] = True
            vote_info['forced'] = True

            self.data_manager.set_val(title, vote_info, ctx.guild_id)
            await self.vote_update(ctx, title, ctx.guild_id)
            await ctx.send(f'以將投票「{title}」關閉！', hidden=True)
        else:
            raise KeyError('vote', f'投票「{title}」並不存在！')

    vote_open_kwargs = {
        'base': 'vote',
        'name': 'open',
        'description': '重新開啟指定投票。',
        'options': [
            create_option(
                name='title',
                description='投票標題。',
                option_type=3,
                required=True
            ),
            create_option(
                name='close_date',
                description='關閉日期。(格式：YYYY/MM/DD HH:MM，預設為原本設定日期)',
                option_type=3,
                required=False
            )
        ]
    }
    @cog_ext.cog_subcommand(**vote_open_kwargs)
    async def _vote_open(self, ctx: SlashContext, title: str, close_date: Optional[str]=None) -> None:
        """開啟投票指令

        /vote open <title> [close_date]
        開啟一個投票。
        """
        title = title.strip()

        vote_info: Dict[str, Any] = self.data_manager.get_val(title, ctx.guild_id)

        if vote_info:
            vote_info['closed'] = False
            vote_info['forced'] = True
            if close_date:
                vote_info['close_date'] = self.check_close_date(close_date.strip())
            elif vote_info['close_date'] and utc_plus(8) >= datetime.strptime(vote_info['close_date'], DATETIME_FORMAT):
                # 如果沒有指定關閉時間，並且原關閉時間已經過去或沒有設置，將關閉時間設成無限
                vote_info['close_date'] = None

            self.data_manager.set_val(title, vote_info, [ctx.guild_id])
            await self.vote_update(ctx, title, ctx.guild_id)
            await ctx.send(f'以將投票「{title}」開啟！', hidden=True)
        else:
            raise KeyError('vote', f'投票「{title}」並不存在！')

    vote_show_list_kwargs = {
        'base': 'vote',
        'subcommand_group': 'show',
        'name': 'list',
        'description': '以條件篩選並顯示投票。',
        'options': [
            create_option(
                name='state',
                description='投票狀態。(預設為全部)',
                option_type=3,
                required=False,
                choices=[
                  create_choice(
                    name='全部',
                    value='all'
                  ),
                  create_choice(
                    name='開啟',
                    value='open'
                  ),
                  create_choice(
                    name='關閉',
                    value='close'
                  )
                ]
            )
        ]
    }
    @cog_ext.cog_subcommand(**vote_show_list_kwargs)
    async def _vote_show_list(self, ctx: SlashContext, state: str='all') -> None:
        """顯示投票指令

        /vote show [state (all|open|close)]
        以條件篩選並列出每個符合條件的投票。
        """
        matchs: List[str] = []
        for _, title in self.data_manager.keys(ctx.guild_id):
            vote_info: Dict[str, Any] = self.data_manager.get_val(title, ctx.guild_id)
            
            if ((state == 'all') or
                (state == 'open' and not vote_info['closed']) or
                (state == 'close' and vote_info['closed'])):
                    matchs.append(title)
        
        await ctx.send('符合條件的投票：\n'+'\n'.join([title for title in matchs]) if matchs else '沒有符合條件的投票:(', hidden=True)

    vote_show_result_kwargs = {
        'base': 'vote',
        'subcommand_group': 'show',
        'name': 'result',
        'description': '顯示指定投票結果。',
        'options': [
            create_option(
                name='title',
                description='投票標題。',
                option_type=3,
                required=True
            )
        ]
    }
    @cog_ext.cog_subcommand(**vote_show_result_kwargs)
    async def _vote_show_result(self, ctx: SlashContext, title: str) -> None:
        """顯示投票結果指令

        /vote show <title>
        顯示一個投票的投票結果。
        """
        title = title.strip()

        vote_info: Dict[str, Any] = self.data_manager.get_val(title, ctx.guild_id)

        if vote_info:
            embed: discord.Embed = discord.Embed(title=f'「{title}」', color=0x07A0C3)
            embed.set_author(name='投票結果')
            for i, opt in enumerate(vote_info['options']):
                # 建立有投第i個選項的成員id清單
                voted_members: List[str] = [ member_id for member_id, votes in vote_info['voted'].items() if 2**i in get_bit_positions(votes) ]
                
                embed.add_field(name=opt, value='\u200D'+' '.join([f'<@{member_id}>' for member_id in voted_members]), inline=False)

            await ctx.send(embed=embed, hidden=True)
        else:
            raise KeyError('vote', f'投票「{title}」並不存在！')

    vote_jumpto_kwargs = {
        'base': 'vote',
        'name': 'jumpto',
        'description': '傳送至指定投票。',
        'options': [
            create_option(
                name='title',
                description='投票標題。',
                option_type=3,
                required=True
            ),
            create_option(
                name='public',
                description='是否公開至聊天室。(預設為False)',
                option_type=5,
                required=False
            )
        ]
    }
    @cog_ext.cog_subcommand(**vote_jumpto_kwargs)
    async def _vote_jumpto(self, ctx: SlashContext, title: str, public: bool=False) -> None:
        """傳送至投票指令

        /vote jumpto <title> [public]
        尋找投票表單並建立一個傳送門。
        """
        title = title.strip()

        vote_info: Dict[str, Any] = self.data_manager.get_val(title, ctx.guild_id)

        if vote_info:
            for channel in await ctx.guild.fetch_channels():
                for msg_id in vote_info['vote_msgs'][::-1]:
                    try:
                        msg: discord.Message = await channel.fetch_message(msg_id)
                        await ctx.send(f'[點此跳至投票「{title}」]({msg.jump_url})', hidden=not public)
                        return
                    except:
                        pass
            else:
                raise KeyError('vote', f'投票「{title}」沒有投票訊息！請使用 `/vote repost` 讓機器人再重新傳送一個投票訊息。')
        else:
            raise KeyError('vote', f'投票「{title}」並不存在！')

    vote_notify_kwargs = {
        'base': 'vote',
        'name': 'notify',
        'description': '列出還沒有投票的成員。',
        'options': [
            create_option(
                name='title',
                description='投票標題。',
                option_type=3,
                required=True
            ),
            create_option(
                name='public',
                description='是否公開至聊天室。(預設為False)',
                option_type=5,
                required=False
            )
        ]
    }
    @cog_ext.cog_subcommand(**vote_notify_kwargs)
    async def _vote_notify(self, ctx: SlashContext, title: str, public: bool=False) -> None:
        """投票通知指令

        /vote notify <title> [public]
        列出尚未投票的成員們。
        """
        title = title.strip()

        vote_info: Dict[str, Any] = self.data_manager.get_val(title, ctx.guild_id)

        if vote_info:
            member_ids: str = ' '.join([ f'<@{member.id}>' for member in ctx.guild.members if str(member.id) not in vote_info['voted'] and member != self.bot.user ])
            if member_ids:
                await ctx.send(f'還沒有投「{title}」的成員有：\n{member_ids}', hidden=not public)
            else:
                await ctx.send('全部成員已經都投過此投票！', hidden=True)
        else:
            raise KeyError('vote', f'投票「{title}」並不存在！')

    vote_repost_kwargs = {
        'base': 'vote',
        'name': 'repost',
        'description': '重新傳送一個投票訊息。',
        'options': [
            create_option(
                name='title',
                description='投票標題。',
                option_type=3,
                required=True
            )
        ]
    }
    @cog_ext.cog_subcommand(**vote_repost_kwargs)
    async def _vote_repost(self, ctx: SlashContext, title: str) -> None:
        """重新傳送投票表單指令

        /vote repost <title>
        重新傳送一個投票表單。
        """
        title = title.strip()

        vote_info: Dict[str, Any] = self.data_manager.get_val(title, ctx.guild_id)

        if vote_info:
            vote_msg: SlashMessage = await ctx.send(embed=self.make_embed(title, vote_info), components=[self.make_select(title, vote_info)])
            vote_info['vote_msgs'].append(str(vote_msg.id))
            self.data_manager.set_val(title, vote_info, [ctx.guild_id])
        else:
            raise KeyError('vote', f'投票「{title}」並不存在！')

    async def vote_update(self, ctx: Union[commands.Bot, SlashContext, ComponentContext], title: str, guild_id: Union[str, int]) -> None:
        """更新投票表單

        更新伺服器上每個對應投票表單上的內容。
        """
        vote_info: Dict[str, Any] = self.data_manager.get_val(title, guild_id)

        if vote_info:
            embed:   discord.Embed  = self.make_embed(title, vote_info)
            select:  Dict[str, Any] = self.make_select(title, vote_info)
            msg_id_list: List[str] = vote_info['vote_msgs']
            edited_msg_id_list: Set[str] = set()
            guild: discord.Guild
            
            if isinstance(ctx, (SlashContext, ComponentContext)):
                guild = ctx.guild
            else:
                guild = ctx.get_guild(int(guild_id))
            
            async def edit_message_in_channel(channel: discord.abc.GuildChannel) -> None:
                for msg_id in msg_id_list:
                    try:
                        msg: discord.Message = await channel.fetch_message(msg_id)
                        await msg.edit(embed=embed, components=[select])
                        edited_msg_id_list.add(msg_id)
                    except:
                        pass
            
            tasks: List[asyncio.Task] = [ asyncio.create_task(edit_message_in_channel(channel)) for channel in guild.channels ]

            await asyncio.wait(tasks)
            
            for msg_id in [ msg_id for msg_id in msg_id_list if msg_id not in edited_msg_id_list ]:
                # 將找不到的投票訊息(被成員手動刪除)從資料庫刪除
                vote_info['vote_msgs'].remove(msg_id)
                self.data_manager.set_val(title, vote_info, guild_id)
        else:
            raise KeyError('vote', f'投票「{title}」並不存在！')

    @cog_ext.cog_component()
    async def vote_select(self, ctx: ComponentContext) -> None:
        """成員投票動作

        成員在表單上使用下拉清單投票後的處理。
        """
        for _, title in self.data_manager.keys(ctx.guild_id):
            vote_info: Dict[str, Any] = self.data_manager.get_val(title, ctx.guild_id)
            if str(ctx.origin_message_id) in vote_info['vote_msgs']:
                if vote_info['closed']:
                    raise PermissionError('vote', '投票失敗，投票「{title}」已經關閉了！')

                vote_info['voted'][str(ctx.author_id)] = sum(2**int(i) for i in ctx.selected_options)

                self.data_manager.set_val(title, vote_info, ctx.guild_id)
                await self.vote_update(ctx, title, ctx.guild_id)
                await ctx.send(content=f"投票成功！\n你投給了：{', '.join([ vote_info['options'][int(i)] for i in ctx.selected_options ])}", hidden=True)
                break
        else:
            raise KeyError('vote', f'投票失敗，投票「{title}」並不存在！')

    def make_embed(self, title: str, vote_info: Dict[str, Any]) -> discord.Embed:
        """製作投票表單

        製作一個投票表單。
        """
        date_text: str = ''
        if vote_info['closed']:
            if vote_info['forced']:
                if vote_info['close_date']:
                    date_text += f"```diff\n- 以被手動關閉，原關閉日期：{vote_info['close_date']} -\n```"
                else:
                    date_text += f"```diff\n- 以被手動關閉 -\n```"
            else:
                if vote_info['close_date']:
                    date_text += f"```diff\n- 以於{vote_info['close_date']}關閉 -\n```"
                else:
                    date_text += f"```diff\n- 以關閉 -\n```"
        else:
            if vote_info['forced']:
                if vote_info['close_date']:
                    date_text += f"```yaml\n- 已重新開啟，{vote_info['close_date']}時關閉 -\n```"
                else:
                    date_text += f"```yaml\n- 已重新開啟，無關閉日期 -\n```"
            else:
                if vote_info['close_date']:
                    date_text += f"```yaml\n- {vote_info['close_date']}時關閉 -\n```"
                else:
                    date_text += f"```yaml\n- 無關閉日期 -\n```"

        embed: discord.Embed = discord.Embed(
            title=f'「{title}」',
            color=0xD64933 if vote_info['closed'] else 0x20B05C
        )
        embed.set_author(name='投票')
        for i, opt in enumerate(vote_info['options']):
            voted_members: List[str] = [ member_id for member_id, votes in vote_info['voted'].items() if 2**i in get_bit_positions(votes) ]
            value: str = f"票數：{len(voted_members):3}"
            if vote_info['show_members']:
                value += '\n' + ' '.join([ f'<@{member_id}>' for member_id in voted_members ])
            if i == len(vote_info['options'])-1:
                value += f'\n{date_text}'

            embed.add_field(name=opt, value=value, inline=False)
        embed.set_footer(text='≡'*43 + '\n' + ('投票已關閉' if vote_info['closed'] else '點擊下面選單以投票'))
        return embed

    def make_select(self, title: str, vote_info: Dict[str, Any]) -> Dict[str, Any]:
        """製作投票表單的下拉清單

        製作投票表單的下拉清單。
        """
        select = create_actionrow(create_select(
            options=[create_select_option(opt, value=str(i)) for i, opt in enumerate(vote_info['options'])],
            custom_id='vote_select',
            placeholder='選擇1個選項' if vote_info['max_votes'] == 1 else f"選擇最多{vote_info['max_votes']}個選項",
            min_values=1,
            max_values=vote_info['max_votes'],
            disabled=vote_info['closed'],
        ))
        return select

    def check_close_date(self, close_date: str) -> str:
        """檢查關閉時間是否合法

        如果關閉時間格式錯誤，或時間已經過去，則錯誤跳出。
        """
        tmp_close_date: datetime
        try:
            tmp_close_date = datetime.strptime(close_date, DATETIME_FORMAT)
            close_date = tmp_close_date.strftime(DATETIME_FORMAT)
        except:
            raise ValueError('vote', 'close_date格式錯誤。(格式：YYYY/MM/DD HH:MM)')

        if tmp_close_date <= utc_plus(8):
            raise ValueError('vote', f'{close_date}已經過去了！')

        return close_date

def setup(bot: commands.Bot) -> None:
    """設置投票模組

    將投票模組加入機器人。
    """
    bot.add_cog( Vote(bot) )