import unittest
from unittest.mock import patch, Mock
import os
import llm_runtime as llm

class Routing(unittest.TestCase):
    def test_subscription_success_never_calls_api(self):
        api = Mock()
        with patch.object(llm, 'codex', return_value='{"tipo":"nota"}'), patch.object(llm, 'argon') as fallback:
            self.assertEqual(llm.complete_json('test', api_client=api), '{"tipo":"nota"}')
        fallback.assert_not_called()
        api.messages.create.assert_not_called()

    def test_argon_precedes_paid_fallback(self):
        api = Mock()
        audit = Mock()
        with patch.object(llm, 'codex', side_effect=RuntimeError()), patch.object(llm, 'argon', return_value='{"tipo":"nota"}'):
            llm.complete_json('test', api_client=api, audit=audit)
        api.messages.create.assert_not_called()
        self.assertEqual([c.args[0] for c in audit.call_args_list], ['codex', 'argon'])

    def test_paid_fallback_only_after_both_fail(self):
        api = Mock(); api.messages.create.return_value.content = [Mock(text='{"tipo":"nota"}')]
        with patch.object(llm, 'codex', side_effect=RuntimeError()), patch.object(llm, 'argon', side_effect=ValueError()):
            llm.complete_json('test', api_client=api)
        self.assertEqual(api.messages.create.call_count, 1)

    def test_invalid_empty_hearing_rejected(self):
        with self.assertRaises(ValueError): llm.validated_text('{"tipo":"rinvio","eventi":[]}')
        with self.assertRaises(ValueError): llm.validated_text('{"tipo":"unknown"}')

    def test_child_never_inherits_service_secrets(self):
        with patch.dict(os.environ, {'TELEGRAM_BOT_TOKEN':'secret', 'ANTHROPIC_API_KEY':'secret', 'SAI2_TOKEN_CODY':'secret', 'CREDENTIALS_DIRECTORY':'private'}):
            env = llm.child_env('codex')
        for key in ('TELEGRAM_BOT_TOKEN','ANTHROPIC_API_KEY','SAI2_TOKEN_CODY','CREDENTIALS_DIRECTORY'):
            self.assertNotIn(key, env)

    def test_real_argon_envelope_response_field(self):
        with patch.object(llm,'run_process',return_value=__import__('json').dumps({'status':'SUCCESS','response':__import__('json').dumps({'tipo':'nota'})})):
            self.assertIn('nota',llm.argon('test'))

    def test_logging_failure_does_not_trigger_paid_fallback(self):
        api=Mock()
        with patch.object(llm,'codex',return_value='{"tipo":"nota"}'),patch.object(llm,'argon') as fallback:
            self.assertIn('nota',llm.complete_json('test',api_client=api,audit=Mock(side_effect=OSError())))
        fallback.assert_not_called();api.messages.create.assert_not_called()

if __name__ == '__main__': unittest.main()
