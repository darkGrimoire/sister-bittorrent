# import asyncio

# async def coro():
#     i = 0
#     while True:
#         await asyncio.sleep(1)
#         print(i)
#         i += 1

# async def complete():
#     print('complete')

# async def main():
#     task = asyncio.create_task(coro())
#     while True:
#         await asyncio.sleep(5)
#         print(task)
#         task.cancel()
#         await complete()

# if __name__ == "__main__":
#     loop = asyncio.get_event_loop()
#     loop.run_until_complete(main())

# import asyncio

# async def main():
#     q = asyncio.Queue()
#     await q.put((1,3))
#     await q.put((2,3))
#     if (1,3) in q:
#         print('it is')
#     else:
#         print('its not')

# if __name__ == "__main__":
#     loop = asyncio.get_event_loop()
#     loop.run_until_complete(main())

# if __name__ == "__main__":
#     import time
#     start = time.time()
#     count = 0
#     for i in range(200000):
#         if i % 123:
#             count += 1
#     end = time.time()
#     print(count)
#     print(end - start)

# import bitstring

# if __name__ == "__main__":
#     a = bitstring.BitArray(10)
#     a[0] = True
#     a[3] = True
#     a[7] = True
#     print(f'{a.bin}')
#     a = a.tobytes()
#     print(f'{a}')
#     a = bitstring.BitArray(bytes=a)
#     print(f'{a.bin}')
#     for idx, piece in enumerate(a):
#         if piece:
#             print(f'true in {idx}')

import asyncio

async def handle_echo(reader, writer):
    data = await reader.read(100)
    message = data.decode()
    addr_repr = ':'.join(map(str, writer.get_extra_info('peername')))
    print("Received %r from %s" % (message, addr_repr))

    if message != 'Hello World!':
        print('mismatch.')
        writer.close()
        return
    print("Send: %r" % message)
    writer.write(data)
    await writer.drain()

    print("Close the client socket")
    writer.close()


loop = asyncio.get_event_loop()
coro = asyncio.start_server(handle_echo, '127.0.0.1', 8888, loop=loop)
server = loop.run_until_complete(coro)

# Serve requests until Ctrl+C is pressed
print('Serving on {}'.format(server.sockets[0].getsockname()))
try:
    loop.run_forever()
except KeyboardInterrupt:
    pass

# Close the server
server.close()
loop.run_until_complete(server.wait_closed())
loop.close()