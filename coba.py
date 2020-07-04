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

import bitstring

if __name__ == "__main__":
    a = bitstring.BitArray(10)
    a[0] = True
    a[3] = True
    a[7] = True
    print(f'{a.bin}')
    a = a.tobytes()
    print(f'{a}')
    a = bitstring.BitArray(bytes=a)
    print(f'{a.bin}')
    for idx, piece in enumerate(a):
        if piece:
            print(f'true in {idx}')
    