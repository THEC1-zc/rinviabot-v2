import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, AsyncMock, patch
import bot
from conversations import ConversationStore

EVENT={'parte':'PersonaAnonima','giudice':'Farinella','luogo':'Tribunale Civitavecchia','data':'15/12/2030','ora':'10:30','note':'Synthetic test'}

def update(text='',actor=20,callback=None):
    message=SimpleNamespace(text=text,message_id=10,reply_text=AsyncMock(),chat=SimpleNamespace(send_action=AsyncMock()))
    result=SimpleNamespace(message=message,effective_message=message,effective_chat=SimpleNamespace(id=10),effective_user=SimpleNamespace(id=actor,username='anonymous'),callback_query=None)
    if callback:result.callback_query=SimpleNamespace(data=callback,answer=AsyncMock(),edit_message_text=AsyncMock())
    return result

class Dialogue(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'state.sqlite'
        self.ctx=SimpleNamespace(bot_data={'_conversation_store':ConversationStore(self.path)})
        self.patches=[patch.object(bot,'log_pipeline_event'),patch.object(bot,'log_telegram_raw_message')]
        for p in self.patches:p.start()
    def tearDown(self):
        for p in self.patches:p.stop()
        self.tmp.cleanup()
    def pending(self,events=None):
        return bot.set_pending_clarification(self.ctx,trace_id='anonymous-1',chat_id=10,user_id=20,original_message='Anonymous hearing 15/12/2030 at 10:30',parsed_data={'tipo':'conferma','interpretazione':dict(EVENT),'eventi':events or [],'domanda':'Confermi?'},reason='uncertain')
    async def test_interpretation_only_candidate_can_be_confirmed(self):
        row=self.pending()
        self.assertEqual(row['parsed_data']['eventi'][0]['parte'],'PersonaAnonima')
        with patch.object(bot,'create_google_calendar_event',return_value={'summary':'Anonymous','id':'event-1'}) as write:
            await bot.handle_dialog_text(update('confermo'),self.ctx,row)
        write.assert_called_once();self.assertIsNone(bot.get_pending_clarification(self.ctx,10,20))
    async def test_correction_is_conversation_not_creation(self):
        row=self.pending();changed=dict(EVENT,ora='11:00')
        with patch.object(bot,'parse_message_with_ai_rewrite',return_value={'tipo':'rinvio','eventi':[changed]}) as parse,patch.object(bot,'create_google_calendar_event') as write:
            await bot.handle_dialog_text(update('alle 11'),self.ctx,row)
        write.assert_not_called();self.assertEqual(parse.call_args.args[0],row['original_message'])
        saved=bot.get_pending_clarification(self.ctx,10,20)
        self.assertEqual(saved['parsed_data']['eventi'][0]['ora'],'11:00')
        self.assertTrue(any(t['text']=='alle 11' for t in saved['history']))
    async def test_parser_failure_keeps_original_and_turn(self):
        row=self.pending()
        with patch.object(bot,'parse_message_with_ai_rewrite',return_value=None):
            await bot.handle_dialog_text(update('correction'),self.ctx,row)
        saved=ConversationStore(self.path).get(10,20)
        self.assertEqual(saved['original_message'],row['original_message'])
        self.assertEqual(saved['history'][-1]['text'],'correction')
    async def test_plain_no_asks_for_correction_without_cancelling(self):
        row=self.pending()
        await bot.handle_dialog_text(update('no'),self.ctx,row)
        self.assertIsNotNone(bot.get_pending_clarification(self.ctx,10,20))
    async def test_explicit_cancel_closes_without_writes(self):
        row=self.pending()
        with patch.object(bot,'create_google_calendar_event') as write:await bot.handle_dialog_text(update('annulla'),self.ctx,row)
        write.assert_not_called();self.assertIsNone(bot.get_pending_clarification(self.ctx,10,20))
    async def test_other_group_member_cannot_confirm(self):
        row=self.pending();u=update(actor=21,callback=f"clarify:confirm:{row['_id']}:{row['_rev']}")
        with patch.object(bot,'create_google_calendar_event') as write:await bot.handle_clarification_callback(u,self.ctx)
        write.assert_not_called();self.assertTrue(u.callback_query.answer.call_args.kwargs['show_alert'])
    async def test_old_button_cannot_confirm_changed_data(self):
        row=self.pending();old=f"clarify:confirm:{row['_id']}:{row['_rev']}"
        row['parsed_data']['eventi'][0]['ora']='11:00';bot.dialog_store(self.ctx).save(row)
        with patch.object(bot,'create_google_calendar_event') as write:await bot.handle_clarification_callback(update(callback=old),self.ctx)
        write.assert_not_called()
    async def test_missing_time_is_never_created(self):
        row=self.pending([dict(EVENT,ora='')])
        with patch.object(bot,'create_google_calendar_event') as write:await bot.confirm_dialog(update('confermo'),self.ctx,row)
        write.assert_not_called();self.assertIsNotNone(bot.get_pending_clarification(self.ctx,10,20))
    async def test_retry_uses_same_intent_and_blocks_corrections_while_uncertain(self):
        row=self.pending()
        with patch.object(bot,'create_google_calendar_event',return_value=None):await bot.confirm_dialog(update('confermo'),self.ctx,row)
        saved=bot.get_pending_clarification(self.ctx,10,20);key=saved['write_trace']
        with patch.object(bot,'parse_message_with_ai_rewrite') as parse:await bot.handle_dialog_text(update('alle 12'),self.ctx,saved)
        parse.assert_not_called();saved=bot.get_pending_clarification(self.ctx,10,20)
        with patch.object(bot,'create_google_calendar_event',return_value={'id':'event-1','summary':'Anonymous'}) as write:await bot.confirm_dialog(update('confermo'),self.ctx,saved)
        self.assertEqual(write.call_args.args[1],key)
    async def test_second_case_parks_first_and_can_be_resumed(self):
        one=self.pending();await bot.handle_new(update('/nuovo'),self.ctx)
        self.assertIsNone(bot.get_pending_clarification(self.ctx,10,20))
        two=self.pending()
        self.assertNotEqual(one['_id'],two['_id'])
        self.assertEqual(len(bot.dialog_store(self.ctx).list_open(10,20)),2)
        selected=bot.dialog_store(self.ctx).select(one['_id'],10,20)
        self.assertEqual(selected['original_message'],one['original_message'])

    async def test_message_handler_opens_and_continues_same_thread(self):
        with patch.object(bot,'parse_message_with_ai',return_value={'tipo':'conferma','interpretazione':dict(EVENT),'eventi':[],'domanda':'Confermi?'}) as initial:
            await bot.handle_message(update('Anonymous full hearing'),self.ctx)
        first=bot.get_pending_clarification(self.ctx,10,20)
        self.assertIsNotNone(first)
        with patch.object(bot,'parse_message_with_ai') as new_parse,patch.object(bot,'parse_message_with_ai_rewrite',return_value={'tipo':'rinvio','eventi':[dict(EVENT,ora='11:00')]}):
            await bot.handle_message(update('alle 11'),self.ctx)
        new_parse.assert_not_called()
        self.assertEqual(bot.get_pending_clarification(self.ctx,10,20)['_id'],first['_id'])

    async def test_mask_ambiguity_enters_the_same_conversation(self):
        form=bot.set_mask_form(self.ctx,trace_id='mask-anonymous',chat_id=10,user_id=20,username='anonymous')
        form['fields']['rinvio']='15/12/2030 10:30'
        u=update(callback='mask:create')
        with patch.object(bot,'parse_message_with_ai',return_value={'tipo':'conferma','interpretazione':dict(EVENT),'eventi':[],'domanda':'Quale giudice?'}),patch.object(bot,'create_google_calendar_event') as write:
            await bot.handle_mask_callback(u,self.ctx)
        write.assert_not_called()
        self.assertIsNotNone(bot.get_pending_clarification(self.ctx,10,20))
        self.assertIsNone(bot.get_mask_form(self.ctx,10,20))

    async def test_past_date_question_keeps_followup_context(self):
        with patch.object(bot,'parse_message_with_ai',return_value={'tipo':'data_passata','data_letta':'01/01/2000','opzioni':[{'id':'a','data':'15/12/2030'}]}):
            await bot.handle_message(update('Anonymous old date'),self.ctx)
        self.assertIsNotNone(bot.get_pending_clarification(self.ctx,10,20))
        with patch.object(bot,'parse_message_with_ai_rewrite',return_value={'tipo':'rinvio','eventi':[dict(EVENT)]}),patch.object(bot,'create_google_calendar_event') as write:
            await bot.handle_message(update('a'),self.ctx)
        write.assert_not_called()
        self.assertEqual(bot.get_pending_clarification(self.ctx,10,20)['parsed_data']['eventi'][0]['data'],'15/12/2030')

if __name__=='__main__':unittest.main()
