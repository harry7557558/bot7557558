import discord
import os
import datetime

import hello
import polynomial
import word_count
import desmos
import shadertoy
import text_preview
import trigger


async def send_text_message(channel, message):
    if len(message) > 1800:
        with open('.temp', 'w') as fp:
            fp.write(message)
        with open(".temp", "r") as fp:
            await channel.send(file=discord.File(fp, "result.txt"))
    else:
        await channel.send(message)


client = discord.Client()


@client.event
async def on_ready():
    message = 'Logged in as `{0.user}`.'.format(client)
    print(message)
    channel = client.get_channel(947155714059665458)
    await channel.send(message)


@client.event
async def on_message(message):
    if os.name == 'nt' and message.guild.id != 822212636619309056:
        return  # testing
    if message.author == client.user:
        return

    # Create a conflict with JOMD
    if message.content.startswith('+gimmie'):
        await message.channel.send(":monkey:")
        return

    # :eyes:
    for start in "$+=,.;?!^&%\\/~-":
        if message.content.lower().startswith(start+'hello'):
            await hello.send_hello_message(message)
            return

    # Mathy stuff
    if message.content.startswith('poly '):
        expr = message.content[len('poly '):]
        expr = expr.strip().strip('`')
        expanded = '`' + polynomial.polyeval(expr) + '`'
        await send_text_message(message.channel, expanded)
        return

    # Word stats
    command = message.content.split(' ')[0].lower()
    if command != '' and command[0] in ['+', '$'] and \
        ('word' in command or 'code' in command or 'char' in command) and \
            ('count' in command or 'stat' in command):
        print(command)
        await word_count.message_main(message)
        return

    # Desmos/Shadertoy stuff
    await desmos.message_main(message)
    await shadertoy.message_main(message)
    await text_preview.message_main(client, message)

    # Keep this at the end
    triggered_embed = trigger.detect_trigger(message)
    if triggered_embed != None:
        await message.channel.send(embed=triggered_embed)
        return


@client.event
async def on_message_edit(before, after):
    if after.author == client.user:
        return

    triggered_embed = trigger.detect_trigger(after)
    if triggered_embed is not None:
        await after.channel.send(embed=triggered_embed)

    ghostping_embed = trigger.detect_ghost_ping(before, after)
    if ghostping_embed is not None:
        await after.channel.send(embed=ghostping_embed)


@client.event
async def on_message_delete(message):
    if message.author == client.user:
        return

    ghostping_embed = trigger.detect_ghost_ping(message)
    if ghostping_embed is not None:
        await message.channel.send(embed=ghostping_embed)


if __name__ == "__main__":
    intents = discord.Intents()
    intents.messages = True
    try:
        # my local Windows
        client.run(open(".token").read())
    except:
        # repl.it
        __import__("keep_alive").keep_alive()
        client.run(os.getenv('TOKEN'))
