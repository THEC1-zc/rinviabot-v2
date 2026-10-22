"""Live subscription-only synthetic extraction probe; no calendar or Telegram writes."""
from launch import configure
configure()
import llm_runtime
prompt = 'Rispondi SOLO con JSON {"tipo":"nota"}. Non usare strumenti.'
print('codex', llm_runtime.codex(prompt), flush=True)
print('argon', llm_runtime.argon(prompt), flush=True)
import bot
bot.client = None
result = bot.parse_message_with_ai('PersonaAnonima: udienza 15/12/2030 ore 10:30 giudice Farinella, Tribunale Civitavecchia. Prova tecnica.')
assert result and result['tipo'] == 'rinvio' and len(result.get('eventi', [])) == 1
print('extraction', result['tipo'], len(result['eventi']), flush=True)
