import unittest

import server


class ServerTests(unittest.TestCase):
    def test_server_rejects_duplicate_port_binding(self):
        self.assertFalse(server.ExclusiveThreadingHTTPServer.allow_reuse_address)


if __name__ == "__main__":
    unittest.main()
