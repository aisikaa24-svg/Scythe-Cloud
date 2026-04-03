import { NextResponse } from 'next/server';

export async function POST(request: Request) {
  const TELEGRAM_BOT_TOKEN = process.env.TELEGRAM_BOT_TOKEN;
  const GITHUB_PAT = process.env.GITHUB_PAT;
  const repoOwner = 'aisikaa24-svg';
  const repoName = 'Scythe-Cloud';
  const workflowId = 'scrape.yml';

  if (!TELEGRAM_BOT_TOKEN || !GITHUB_PAT) {
    return NextResponse.json({ error: 'Config missing' }, { status: 500 });
  }

  try {
    const body = await request.json();
    const message = body.message?.text;
    const chatId = body.message?.chat?.id;

    if (!message || !chatId) {
      return NextResponse.json({ ok: true }); // Acknowledge message silently
    }

    if (message.toLowerCase() === '/run' || message.toLowerCase() === '/extract') {
      // 1. Reply to user: Mission Start
      await fetch(`https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          chat_id: chatId,
          text: '🚀 SCYTHE: Extraction Mission Initialized! Stand by for vectors...'
        })
      });

      // 2. Trigger GitHub Action
      const response = await fetch(`https://api.github.com/repos/${repoOwner}/${repoName}/actions/workflows/${workflowId}/dispatches`, {
        method: 'POST',
        headers: {
          'Accept': 'application/vnd.github.v3+json',
          'Authorization': `Bearer ${GITHUB_PAT}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ ref: 'main' })
      });

      if (!response.ok) {
        // Inform user if trigger failed
        await fetch(`https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            chat_id: chatId,
            text: '❌ ERROR: Failed to trigger mission. Is GITHUB_PAT set correctly?'
          })
        });
      }
    } else {
        // Handle other messages
        await fetch(`https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              chat_id: chatId,
              text: 'SCYTHE CORE: Commands available:\n/run - Start extraction\n/extract - Start extraction'
            })
          });
    }

    return NextResponse.json({ ok: true });
  } catch (err: any) {
    console.error('Webhook error:', err);
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
