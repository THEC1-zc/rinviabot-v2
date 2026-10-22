import tempfile
from pathlib import Path
import unittest
from conversations import ConversationStore

class DurableThreads(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory();self.path = Path(self.temp.name)/'db.sqlite'
        self.store = ConversationStore(self.path)
    def tearDown(self):self.temp.cleanup()
    def sample(self, actor=2):return {'chat_id':1,'user_id':actor,'history':[{'role':'user','text':'Anonymous fixture'}],'parsed_data':{}}
    def test_survives_new_process_store(self):
        saved=self.store.save(self.sample())
        self.assertEqual(ConversationStore(self.path).get(1,2),saved)
    def test_group_actors_are_isolated(self):
        one=self.store.save(self.sample(2));two=self.store.save(self.sample(3))
        self.assertNotEqual(one['_id'],two['_id'])
        self.assertIsNone(self.store.select(one['_id'],1,3))
    def test_stale_revision_cannot_overwrite_new_correction(self):
        row=self.store.save(self.sample());old=dict(row)
        row['history'].append({'role':'user','text':'at 11'});self.store.save(row)
        with self.assertRaises(ValueError):self.store.save(old)
    def test_parking_preserves_multiple_doubts(self):
        one=self.store.save(self.sample());self.store.park(1,2)
        self.assertIsNone(self.store.get(1,2))
        self.store.save(self.sample())
        self.assertEqual(len(self.store.list_open(1,2)),2)
        self.assertEqual(self.store.select(one['_id'],1,2)['_id'],one['_id'])
    def test_closed_thread_cannot_be_resurrected(self):
        row=self.store.save(self.sample());self.store.close(1,2)
        with self.assertRaises(ValueError):self.store.save(row)

if __name__=='__main__':unittest.main()
