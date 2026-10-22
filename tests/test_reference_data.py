import unittest
import reference_data as ref

class RoleReference(unittest.TestCase):
    def test_pms_are_not_flat_judge_entries(self):
        for surname in ('aldi','maglione','pignotti'):
            self.assertIn(surname,ref.PROSECUTOR_SURNAMES)
            self.assertNotIn(surname,ref.KNOWN_JUDGES)
    def test_legacy_unknown_is_kept_without_current_service_claim(self):
        self.assertIn('nigro imperiale',ref.KNOWN_JUDGES)
        self.assertFalse(any(p['surname']=='Nigro Imperiale' for p in ref.DATA['magistrates']))
    def test_sodani_homonymy_is_preserved(self):
        names={p['name'] for p in ref.DATA['magistrates'] if p['surname']=='Sodani'}
        self.assertEqual(names,{'Daniele Sodani','Vittoria Sodani'})
    def test_studio_recurrent_colleague_is_recognized(self):
        self.assertIn('sciullo',ref.KNOWN_LAWYERS)
        self.assertEqual(ref.KNOWN_JUDGES['fuccio sanza'],'Fuccio Sanzà')

if __name__=='__main__':unittest.main()
