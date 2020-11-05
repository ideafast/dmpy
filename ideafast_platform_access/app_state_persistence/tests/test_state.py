import unittest
import json
from pathlib import Path

from ideafast_platform_access.app_state_persistence.app_state import AppState
from ideafast_platform_access.dmp_login_state import DmpLoginState
from ideafast_platform_access import dmp_resources
from ideafast_platform_access.dmp_connection import DmpConnection, DmpResponse


class StateTestCase(unittest.TestCase):

    def test_AppState_basics(self):
        appname = 'test_py_app'
        appstate = AppState(appname)
        self.assertTrue(appstate.home.exists())
        statename = 'basics'
        state = {
            "foo": 42,
            "bar": "baz",
        }
        basics_json = appstate.home / 'basics.json'
        basics_tmp = appstate.home / 'basics.tmp'
        basics_bak = appstate.home / 'basics.bak'
        if basics_tmp.exists():
            basics_tmp.unlink()
        if basics_json.exists():
            basics_json.unlink()
        if basics_bak.exists():
            basics_bak.unlink()
        self.assertFalse(basics_tmp.exists())
        self.assertFalse(basics_json.exists())
        self.assertFalse(basics_bak.exists())
        state2 = appstate.load_state(statename)
        self.assertIsNone(state2)
        state2 = appstate.load_state(statename, "DEFAULT")
        self.assertIsInstance(state2, str)
        self.assertEqual(state2, "DEFAULT")
        appstate.save_state(statename, state)
        self.assertFalse(basics_tmp.exists())
        self.assertTrue(basics_json.exists())
        self.assertFalse(basics_bak.exists())
        appstate.save_state(statename, state)
        self.assertFalse(basics_tmp.exists())
        self.assertTrue(basics_json.exists())
        self.assertTrue(basics_bak.exists())
        state2 = appstate.load_state(statename)
        self.assertIsNotNone(state2)
        self.assertIsInstance(state2, dict)
        self.assertEqual(state2['foo'], 42)
        state2 = appstate.load_state(statename, "DEFAULT")
        self.assertIsNotNone(state2)
        self.assertIsInstance(state2, dict)
        self.assertEqual(state2['foo'], 42)
        appstate.save_state(statename, None)
        self.assertFalse(basics_tmp.exists())
        self.assertFalse(basics_json.exists())
        self.assertTrue(basics_bak.exists())
        state2 = appstate.load_state(statename)
        self.assertIsNone(state2)
        pass

    def test_DmpState(self):
        ds = DmpLoginState('test_py_dmp')

        ds._erase()
        self.assertIsNone(ds.state_stamp)
        self.assertFalse(ds.has_username)
        self.assertFalse(ds.is_logged_in)

        ds.change_user(None, None, None)
        self.assertIsNotNone(ds.state_stamp)
        self.assertFalse(ds.has_username)
        self.assertFalse(ds.is_logged_in)

        ds.change_user('someuser', None, None)
        self.assertIsNotNone(ds.state_stamp)
        self.assertTrue(ds.has_username)
        self.assertFalse(ds.is_logged_in)

        ds.login('not-a-valid-login', {})
        self.assertIsNotNone(ds.state_stamp)
        self.assertTrue(ds.has_username)
        self.assertTrue(ds.is_logged_in)

        ds2 = DmpLoginState('test_py_dmp')
        self.assertIsNotNone(ds2.state_stamp)
        self.assertTrue(ds2.has_username)
        self.assertTrue(ds2.is_logged_in)

        ds.logout()
        self.assertIsNotNone(ds.state_stamp)
        self.assertTrue(ds.has_username)
        self.assertFalse(ds.is_logged_in)

        ds.change_user('someuser', 'not-a-valid-login', {})
        self.assertIsNotNone(ds.state_stamp)
        self.assertTrue(ds.has_username)
        self.assertTrue(ds.is_logged_in)

        ds.change_user('someuser', None, None)
        self.assertIsNotNone(ds.state_stamp)
        self.assertTrue(ds.has_username)
        self.assertFalse(ds.is_logged_in)

        ds._erase()
        self.assertIsNone(ds.state_stamp)
        self.assertFalse(ds.has_username)
        self.assertFalse(ds.is_logged_in)

        pass

    def test_resources(self):
        gql = dmp_resources.read_text_resource('dmp_login.graphql')
        self.assertIsNotNone(gql)
        self.assertIsInstance(gql, str)
        print('Read text: ----------------------------------------------')
        print(gql)
        print('---------------------------------------------------------')
        pass

    def test_user_info(self):
        dc = DmpConnection('test_py_dmp_ro')
        self.assertTrue(dc.is_logged_in)
        info = dc.user_info_request()
        self.assertIsNotNone(info)
        info2 = {
            'user': info.content,
            'cookies': info.cookies,
            'status': info.status,
        }
        print('Response =')
        print(json.dumps(info2, indent=2))
        self.assertIsInstance(info, DmpResponse)
        pass


if __name__ == '__main__':
    unittest.main()
