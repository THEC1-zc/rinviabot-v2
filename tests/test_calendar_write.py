import copy
from types import SimpleNamespace
import unittest
from calendar_write import insert_verified

class Missing(Exception):
    resp=SimpleNamespace(status=404)
class Command:
    def __init__(self,fn):self.fn=fn
    def execute(self):return self.fn()
class Calendar:
    def __init__(self):self.rows={};self.writes=0;self.timeout_after_insert=False;self.read_error=False
    def events(self):return self
    def get(self,calendarId,eventId):
        def read():
            if self.read_error:raise TimeoutError()
            if eventId not in self.rows:raise Missing()
            return copy.deepcopy(self.rows[eventId])
        return Command(read)
    def insert(self,calendarId,body):
        def write():
            self.writes+=1;self.rows[body['id']]=copy.deepcopy(body)
            if self.timeout_after_insert:raise TimeoutError()
            return copy.deepcopy(body)
        return Command(write)

class VerifiedWrites(unittest.TestCase):
    def setUp(self):
        self.service=Calendar();self.event={'summary':'Anonymous test','start':{'dateTime':'2030-12-15T10:30:00+01:00'},'end':{'dateTime':'2030-12-15T11:30:00+01:00'},'reminders':{'useDefault':False,'overrides':[]}}
    def test_double_confirmation_writes_once(self):
        first=insert_verified(self.service,'calendar',self.event,'thread-1')
        second=insert_verified(self.service,'calendar',self.event,'thread-1')
        self.assertEqual(first['id'],second['id']);self.assertEqual(self.service.writes,1)
    def test_insert_timeout_is_reconciled_without_second_insert(self):
        self.service.timeout_after_insert=True
        self.assertIn('id',insert_verified(self.service,'calendar',self.event,'thread-1'))
        self.assertEqual(self.service.writes,1)
    def test_changed_payload_is_conflict_not_an_overwrite(self):
        insert_verified(self.service,'calendar',self.event,'thread-1')
        changed=dict(self.event,summary='Different')
        with self.assertRaises(RuntimeError):insert_verified(self.service,'calendar',changed,'thread-1')
        self.assertEqual(self.service.writes,1)
    def test_external_edit_is_detected_on_readback(self):
        found=insert_verified(self.service,'calendar',self.event,'thread-1')
        self.service.rows[found['id']]['summary']='External edit'
        with self.assertRaises(RuntimeError):insert_verified(self.service,'calendar',self.event,'thread-1')
    def test_unknown_read_failure_does_not_insert(self):
        self.service.read_error=True
        with self.assertRaises(TimeoutError):insert_verified(self.service,'calendar',self.event,'thread-1')
        self.assertEqual(self.service.writes,0)
    def test_cancelled_event_is_never_recreated(self):
        found=insert_verified(self.service,'calendar',self.event,'thread-1')
        self.service.rows[found['id']]['status']='cancelled'
        with self.assertRaises(RuntimeError):insert_verified(self.service,'calendar',self.event,'thread-1')
        self.assertEqual(self.service.writes,1)

if __name__=='__main__':unittest.main()
