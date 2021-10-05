from discord.ext import commands
from discord_slash.context import SlashContext, ComponentContext
import traceback

def setup(bot: commands.Bot) -> None:
    """設置錯誤處理器
    
    接收所有指令與元件的錯誤，以將自定義錯誤訊息回傳到使用者。
    """
    
    @bot.event
    async def on_slash_command_error(ctx: SlashContext, ex: Exception) -> None:
        """
        接收所有指令錯誤
        """
        if ex.args and ex.args[0] in ('vote', 'permission'):
            await ctx.send(content=ex.args[1], hidden=True)
        else:
            traceback.print_tb(ex.__traceback__)
            print(ex)

    @bot.event
    async def on_component_callback_error(ctx: ComponentContext, ex: Exception) -> None:
        """
        接收所有元件錯誤
        """
        if ex.args and ex.args[0] in ('vote', 'permission'):
            await ctx.send(content=ex.args[1], hidden=True)
        else:
            traceback.print_tb(ex.__traceback__)
            print(ex)