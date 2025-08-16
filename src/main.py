from tempfile import TemporaryDirectory
from subprocess import TimeoutExpired
from io import StringIO
from discord.ext import commands
import discord

import config
import code_runner


bot = commands.Bot(
    command_prefix='k!',
    intents=discord.Intents(messages=True, message_content=True)
)


def finalize_output(stdout: str, stderr: str) -> tuple[str, str]:
    """
    Removes leading and trailing whitespace and removes any '`' characters.\n
    Output is wrapped in '```', and in case it is empty, '```[No output]```' is returned.
    """
    stdout, stderr = stdout.strip().replace('`', ''), stderr.strip().replace('`', '')
    stdout = f'```\n{stdout}\n```' if stdout else '```\n[No output]\n```'
    stderr = f'```\n{stderr}\n```' if stderr else '```\n[No output]\n```'
    return stdout, stderr


@bot.event
async def on_ready() -> None:
    print('-' * 64)
    print('Bot is ready OwO')


@bot.command(name='e')
async def execute(ctx: commands.Context) -> None:
    if ctx.author.id in config.BLACK_LIST or ctx.channel.type is discord.ChannelType.private:
        await ctx.reply('No...')
        return

    message = await ctx.reply('Running code, please wait...')

    try:
        code, language = code_runner.fetch_code(ctx.message.content)
    except ValueError as err:
        await message.edit(content=err)
        return

    with TemporaryDirectory() as tmpdir:
        try:
            exit_code, stdout, stderr = code_runner.run(code, tmpdir, language)
        except ValueError as err:
            await message.edit(content=err)
            return
        except TimeoutExpired as err:
            await message.edit(content=err)
            return

        stdout, stderr = finalize_output(stdout, stderr)
        content = f'Process exited with code `{exit_code}`\nstdout:\n{stdout}\nstderr:\n{stderr}'

        if len(content) < 2000:
            await message.edit(content=content)
            return

        with StringIO(content) as string:
            attachment = discord.File(string, 'output.txt')
            await message.edit(content='Output is way too long; sent in a file', attachments=(attachment,))


bot.run(config.TOKEN)
