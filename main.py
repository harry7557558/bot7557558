import discord
import os
import datetime

import hello
import polynomial
import desmos
import shadertoy
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
    print('Logged in as {0.user}'.format(client))


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    # Create a conflict with JOMD
    if message.content.startswith('+gimmie'):
        await message.channel.send(":monkey:")
        return

    # What the heck?
    if message.content.startswith('$hello'):
        await hello.send_hello_message(message)
        return

    # Mathy stuff
    if message.content.startswith('poly '):
        expr = message.content[len('poly '):]
        expr = expr.strip().strip('`')
        expanded = '`' + polynomial.polyeval(expr) + '`'
        await send_text_message(message.channel, expanded)
        return

    # Desmos/Shadertoy stuff
    await desmos.message_main(message)
    await shadertoy.message_main(message)

    # Keep this at the end
    triggered_embed = trigger.detect_trigger(message)
    if triggered_embed != None:
        await message.channel.send(embed=triggered_embed)
        return


try:
    # my local Windows
    client.run(open(".token").read())
except:
    # repl.it
    __import__("keep_alive").keep_alive()
    client.run(os.getenv('TOKEN'))
