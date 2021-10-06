from discord import Message, Embed, Guild
from discord.ext import commands, tasks
from discord_slash import cog_ext
from discord_slash.utils.manage_commands import create_option, create_choice
from discord_slash.utils.manage_components import create_select, create_select_option, create_actionrow
from discord_slash.context import SlashContext, ComponentContext
from discord_slash.model import SlashMessage
from typing import Optional, Union, List, Tuple, Dict, Set, Any
import re
from random import choice
from math import log2
from itertools import groupby
from utils import get_bit_positions
from variable import DATETIME_FORMAT
from data_manager import DataManager

class Response(commands.Cog):
    """Response modules
    
    Responses is using a trips/reacts system. If user's message contain trip
    words, bot will randomly choose one of the react words the trip words are
    linking to.
    
    As example below, if user's message contain the word 'trip_1', the bot
    will follow the link and find the word: 'react_1', and reply the user
    with it; if user's message contain the word 'trip_2', the bot will follow
    the link and find the words: 'react_1' and 'react_2', and reply the user
    with one of it.
    
    data = {
        'trips': [
            {
                'word': 'trip_1',
                'links': 1
            },
            {
                'word': 'trip_2',
                'links': 3
            }
        ],
        'reacts': [
            'react_1',
            'react_2'
        ]
    }
    """
    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot
        self.data_manager = DataManager('response')
        
    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """Check if data exist on ready"""
        for guild in self.bot.guilds:
            if not self.data_manager.get_val(guild.id):
                self.data_manager.set_val(guild.id, { 'trips': [], 'reacts': [] })

    @commands.Cog.listener()
    async def on_guild_join(self, guild: Guild) -> None:
        """Set default data when join the guild"""
        self.data_manager.set_val(guild.id, { 'trips': [], 'reacts': [] })

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: Guild) -> None:
        """Delete the data if remove from guild"""
        self.data_manager.del_val(guild.id)
    
    @commands.Cog.listener()
    async def on_message(self, message: Message) -> None:
        # if the message sender is the bot itself, return
        if message.author == self.bot.user:
            return

        message.content = re.sub("((?:(?:https?|ftp):\/\/)[\w/\-?=%.]+\.[\w/\-&?=%.]+)", '', message.content).lower().replace('\\|', '|')
            
        # print(message.content)

        data: Dict[str, Any] = self.data_manager.get_val(message.guild.id)

        replys = []
        
        for trip in data['trips']:
            if trip['word'] in message.content:
                bit: int = choice(list(get_bit_positions(trip['links'])))
                replys.append(data['reacts'][int(log2(bit))])
        
        if replys:
            await message.reply( '\n'.join( replys ) )  
        
    
    response_add_kwargs = {
        'base': 'response',
        'name': 'add',
        'description': 'Add responses. How responses work: [bot detect trips] -> [bot choose reacts]',
        # 'base_default_permission': False,
        'options': [
            create_option(
                name='trips',
                description='The words bots will detects. (Separate the words with "|")',
                option_type=3,
                required=True
            ),
            create_option(
                name='reacts',
                description='Bot responses, bot will randomly pick a react sentences to send. (Separate the sentences with "|")',
                option_type=3,
                required=True
            ),
            create_option(
                name='hide',
                description='Shhh... Let\'s try not to let others find out what you are adding (Default as False)',
                option_type=5,
                required=False
            )
        ]
    }
    @cog_ext.cog_subcommand(**response_add_kwargs)
    async def _response_add(self, ctx: SlashContext, trips: str, reacts: str, hide: bool = False) -> None:
        """Add responses command

        /response add <trips> <reacts>
        Add responses with trips/reacts system.
        """
        trips                   = trips.lower().strip()
        trip_list: List[str]    = list(dict.fromkeys([ self.to_origin(t).strip() for t in self.to_bracket(trips).split('|') if t ]))
        reacts                  = reacts.strip()
        react_list: List[str]   = list(dict.fromkeys([ self.to_origin(r).strip() for r in self.to_bracket(reacts).split('|') if r ]))

        data: Dict[str, Any] = self.data_manager.get_val(ctx.guild_id)

        react_bits: int = 0
        
        # find exsiting react pos for bits
        # append non-exsiting react 
        # add all pos to get links bits for trips
        for react in react_list:
            if react in data['reacts']:
                react_bits |= 1 << data['reacts'].index(react)
            else:
                i: int = 0
                for i, r in enumerate(data['reacts']):
                    if r is None:
                        data['reacts'][i] = react
                        break
                else:
                    i = len(data['reacts'])
                    data['reacts'].append(react)
                react_bits |= 1 << i

        # modify exsiting trips link bits with 'OR'
        # append non-exsiting trips
        if react_bits and trip_list:
            for trip in trip_list:
                words: List[str] = [ t['word'] for t in data['trips'] ]
                if trip in words:
                    data['trips'][words.index(trip)]['links'] |= react_bits
                else:
                    data['trips'].append({
                        'word': trip,
                        'links': react_bits
                    })

            self.data_manager.set_val(ctx.guild_id, data)

            await ctx.reply(f'{", ".join([ t.strip() for t in trip_list ])} are successfully added!', hidden=hide)
        else:
            miss_text: str = ' or '.join( ([] if trip_list else ['trips']) + ([] if react_list else ['reacts']) )
            raise KeyError('response', f'You did not enter any {miss_text}!')
        

    response_remove_kwargs = {
        'base': 'response',
        'name': 'remove',
        'description': 'Remove responses, if "reacts" field is specified, remove trips\'s link instead',
        'options': [
            create_option(
                name='trips',
                description='The trips you want to remove. (Separate the words with "|")',
                option_type=3,
                required=True
            ),
            create_option(
                name='reacts',
                description='Optional. Specify the reacts you want to remove from responses. (Separate the sentences with "|")',
                option_type=3,
                required=False
            ),
            create_option(
                name='hide',
                description='Shhh... Let\'s try not to let others find out what you are removing (Default as False)',
                option_type=5,
                required=False
            )
        ]
    }
    @cog_ext.cog_subcommand(**response_remove_kwargs)
    async def _response_remove(self, ctx: SlashContext, trips: str, reacts: str = '', hide: bool = False) -> None:
        """Remove responses command

        /response remove <trips> [reacts]
        Remove trips if reacts is not specify.
        Remove trips's links otherwise.
        Follow by cleaning the unlinked reacts.
        """
        trips                   = trips.lower().strip()
        trip_list: List[str]    = list(dict.fromkeys([ self.to_origin(t).strip() for t in self.to_bracket(trips).split('|') if t ]))
        reacts                  = reacts.strip()
        react_list: List[str]   = list(dict.fromkeys([ self.to_origin(r).strip() for r in self.to_bracket(reacts).split('|') if r ]))

        data: Dict[str, Any] = self.data_manager.get_val(ctx.guild_id)
        
        react_bits: int = 0
        existed_trips: List[str] = []
        
        # find exsiting react pos for bits
        # add all pos to get links bits for trips
        if reacts:
            for react in react_list:
                if react in data['reacts']:
                    react_bits |= 1 << data['reacts'].index(react)

        # unlink specify the reacts from trips
        # remove exsiting trips if reacts are not specify 
        for trip in trip_list:
            words: List[str] = [ t['word'] for t in data['trips'] ]
            if trip in words:
                if react_bits:
                    data['trips'][words.index(trip)]['links'] &= ~react_bits
                    if not data['trips'][words.index(trip)]['links']:
                        del data['trips'][words.index(trip)]
                elif react_list:
                    raise KeyError('response', f'Bot won\'t ever reply {", ".join([ f"[{r}]" for r in react_list ])}')
                else:
                    del data['trips'][words.index(trip)]
                existed_trips.append(trip)
        
        exist_bits: int = 0
        for d_trip in data['trips']:
            exist_bits |= d_trip['links']
        for i in range(len(data['reacts'])):
            if (1 << i) not in list(get_bit_positions(exist_bits)):
                data['reacts'][i] = None

        self.data_manager.set_val(ctx.guild_id, data)

        if existed_trips:
            await ctx.reply(f'{", ".join(existed_trips)} are successfully removed!', hidden=hide)
        else:
            raise KeyError('response', f'Are you sure the trips exsit in the first place?')

    @cog_ext.cog_subcommand(
        base='response',
        name='show',
        description='Show responses in a table form.',
        options=[
            create_option(
                name='trips',
                description='Search certain trip words. (Separate the words with "|")',
                option_type=3,
                required=False
            )
        ]
    )
    async def _response_show(self, ctx: SlashContext, trips: str = '') -> None:
        """Show responses command

        /response show [trips]
        Show all responses that contian trips,
        show all responses if trips is not specify.
        """
        trips                   = trips.lower().strip()
        trip_list: List[str]    = list(dict.fromkeys([ self.to_origin(t).strip() for t in self.to_bracket(trips).split('|') if t ]))

        data: Dict[str, Any] = self.data_manager.get_val(ctx.guild_id)

        if not data:
            data = { 'trips': [], 'reacts': [] }
            self.data_manager.set_val(ctx.guild_id, data)
            
        embed: Embed     = Embed(title='Responses')
        words: List[str] = [ t['word'] for t in data['trips'] ]
        trip_links: List[Tuple[int, str]]

        if trip_list:
            trip_links = [ (t['links'], trip) for trip in trip_list for t in data['trips'] if trip == t['word'] ]
        else:
            trip_links = [ (t['links'], t['word']) for t in data['trips'] ]
            
        if trip_links:
            response_list: List[str] = []
            for link, words in [ (l, [ f'"{g[1]}"' for g in gs ]) for l, gs in groupby(sorted(trip_links, key=lambda x:x[0]), key=lambda x:x[0]) ]:
                react_pos_list: List[int] = [ int(log2(bit)) for bit in get_bit_positions(link) ]
                response_list.append( f'[ {", ".join(words)} ]:' + ''.join([ f'\n{data["reacts"][pos]}' for pos in react_pos_list ]) )
                
                if len('\n\n'.join(response_list)) > 1024:
                    embed.add_field(name='\u200b', value='\n\n'.join(response_list[:-1]), inline=False)
                    response_list = [ response_list[-1] ]

            embed.add_field(name='\u200b', value='\n\n'.join(response_list), inline=False)
        else:
            embed.add_field(name='No result of', value=', '.join(trip_list) + '\u200b')
        
        await ctx.reply(embed=embed, hidden=True)
            
            
    def to_bracket(self, s: str) -> str:
        return s.replace('\\|', '[[hor_bar]]').replace('||', '[[spoiler]]')
    
    def to_origin(self, s: str) -> str:
        return s.replace('[[hor_bar]]', '|').replace('[[spoiler]]', '||')
        


def setup(bot: commands.Bot) -> None:
    """設置投票模組

    將投票模組加入機器人。
    """
    bot.add_cog( Response(bot) )