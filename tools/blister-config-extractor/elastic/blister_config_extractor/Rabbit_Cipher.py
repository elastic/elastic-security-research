from struct import unpack

from .Rabbit_Util import ROTL32, Rabbit_ctx, Rabbit_state

# https://github.com/Robin-Pwner/Rabbit-Cipher/


class Rabbit(object):
    def __init__(self, key, iv):
        self.ctx = Rabbit_ctx()
        self.set_iv(iv)
        self.set_key(key)
        if len(iv):
            pass

    def g_func(self, x):
        x = x & 0xFFFFFFFF
        x = (x * x) & 0xFFFFFFFFFFFFFFFF
        result = (x >> 32) ^ (x & 0xFFFFFFFF)
        return result

    def set_key(self, key):
        # generate four subkeys
        key0 = unpack("<I", key[0:4])[0]
        key1 = unpack("<I", key[4:8])[0]
        key2 = unpack("<I", key[8:12])[0]
        key3 = unpack("<I", key[12:16])[0]
        s = self.ctx.m
        # generate initial state variables
        s.x[0] = key0
        s.x[2] = key1
        s.x[4] = key2
        s.x[6] = key3
        s.x[1] = ((key3 << 16) & 0xFFFFFFFF) | ((key2 >> 16) & 0xFFFF)
        s.x[3] = ((key0 << 16) & 0xFFFFFFFF) | ((key3 >> 16) & 0xFFFF)
        s.x[5] = ((key1 << 16) & 0xFFFFFFFF) | ((key0 >> 16) & 0xFFFF)
        s.x[7] = ((key2 << 16) & 0xFFFFFFFF) | ((key1 >> 16) & 0xFFFF)
        # generate initial counter values
        s.c[0] = ROTL32(key2, 16)
        s.c[2] = ROTL32(key3, 16)
        s.c[4] = ROTL32(key0, 16)
        s.c[6] = ROTL32(key1, 16)
        s.c[1] = (key0 & 0xFFFF0000) | (key1 & 0xFFFF)
        s.c[3] = (key1 & 0xFFFF0000) | (key2 & 0xFFFF)
        s.c[5] = (key2 & 0xFFFF0000) | (key3 & 0xFFFF)
        s.c[7] = (key3 & 0xFFFF0000) | (key0 & 0xFFFF)
        s.carry = 0

        # Iterate system four times
        for i in range(4):
            self.next_state(self.ctx.m)

        for i in range(8):
            # modify the counters
            self.ctx.m.c[i] ^= self.ctx.m.x[(i + 4) & 7]
        # Copy master instance to work instance
        self.ctx.w = self.copy_state(self.ctx.m)

    def copy_state(self, state):
        n = Rabbit_state()
        n.carry = state.carry

        for i, j in enumerate(state.x):
            n.x[i] = j
        for i, j in enumerate(state.c):
            n.c[i] = j
        return n

    def set_iv(self, iv):
        # generate four subvectors
        v = [0] * 4
        v[0] = unpack("<I", iv[0:4])[0]
        v[2] = unpack("<I", iv[4:8])[0]
        v[1] = (v[0] >> 16) | (v[2] & 0xFFFF0000)
        v[3] = ((v[2] << 16) | (v[0] & 0x0000FFFF)) & 0xFFFFFFFF
        # Modify work's counter values
        for i in range(8):
            self.ctx.w.c[i] = self.ctx.m.c[i] ^ v[i & 3]
        # Copy state variables but not carry flag
        tmp = []

        for cc in self.ctx.m.x:
            tmp += [cc]
        self.ctx.w.x = tmp

        # Iterate system four times
        for i in range(4):
            self.next_state(self.ctx.w)

    def next_state(self, state):
        g = [0] * 8
        x = [0x4D34D34D, 0xD34D34D3, 0x34D34D34]
        # calculate new counter values
        for i in range(8):
            tmp = state.c[i]
            state.c[i] = (state.c[i] + x[i % 3] + state.carry) & 0xFFFFFFFF
            state.carry = state.c[i] < tmp
        # calculate the g-values
        for i in range(8):
            g[i] = self.g_func(state.x[i] + state.c[i])
        # calculate new state values

        j = 7
        i = 0
        while i < 8:
            state.x[i] = (g[i] + ROTL32(g[j], 16) + ROTL32(g[j - 1], 16)) & 0xFFFFFFFF
            i += 1
            j += 1
            state.x[i] = (g[i] + ROTL32(g[j & 7], 8) + g[j - 1]) & 0xFFFFFFFF
            i += 1
            j += 1
            j &= 7

    def crypt(self, msg):
        plain = []
        msg_len = len(msg)
        c = self.ctx
        x = [0] * 4
        start = 0
        while True:
            self.next_state(c.w)
            for i in range(4):
                x[i] = c.w.x[i << 1]
            x[0] ^= (c.w.x[5] >> 16) ^ (c.w.x[3] << 16)
            x[1] ^= (c.w.x[7] >> 16) ^ (c.w.x[5] << 16)
            x[2] ^= (c.w.x[1] >> 16) ^ (c.w.x[7] << 16)
            x[3] ^= (c.w.x[3] >> 16) ^ (c.w.x[1] << 16)
            b = [0] * 16
            for i, j in enumerate(x):
                for z in range(4):
                    b[z + 4 * i] = 0xFF & (j >> (8 * z))
            for i in range(16):
                plain.append((msg[start] ^ b[i]))
                start += 1
                if start == msg_len:
                    return bytes(plain)


def st(b):
    a = ""
    for x in b:
        a += chr(x)
    return a


if __name__ == "__main__":
    # some test samples
    # fmt: off
    data = [
        27, 189, 4, 251, 8, 225, 3, 68, 215, 122, 236, 142, 150, 146, 64, 183, 32, 250, 137, 226, 4, 132, 74,
        80, 161, 187, 18, 103, 70, 41, 154, 11, 74, 239, 122, 64, 214, 218, 255, 196, 6, 192, 231, 111, 162,
        176, 28, 54, 209, 166, 230, 229, 29, 90, 53, 201, 246, 51, 215, 20, 24, 235, 84, 250, 27, 115, 54, 190,
        99, 69, 173, 177, 83, 57, 122, 53, 52, 167, 71, 50, 252, 153, 104, 213, 15, 150, 163, 116, 248, 44, 135,
        121, 58, 182, 144, 76, 92, 247, 143, 20
    ]
    key = [
        0xC0, 0x54, 0xBE, 0x4A, 0xB3, 0x02, 0x83, 0x2E, 0x38, 0x88, 0x6C, 0x02, 0xE5, 0xD6, 0x85, 0x0C,
    ]
    # fmt: on
    iv = [0x84, 0xE2, 0x67, 0x82, 0x6C, 0x1E, 0x68, 0x4A]

    cipher = Rabbit(bytes(key), bytes(iv))

    data = cipher.crypt(bytes(data))
    print(data)
