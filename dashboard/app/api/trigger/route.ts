import { NextResponse } from 'next/server';

export async function POST() {
  const GITHUB_PAT = process.env.GITHUB_PAT;
  const repoOwner = 'aisikaa24-svg';
  const repoName = 'Scythe-Cloud';
  const workflowId = 'scrape.yml'; // Name of the workflow file

  if (!GITHUB_PAT) {
    return NextResponse.json({ error: 'GitHub PAT is not configured' }, { status: 500 });
  }

  try {
    const response = await fetch(`https://api.github.com/repos/${repoOwner}/${repoName}/actions/workflows/${workflowId}/dispatches`, {
      method: 'POST',
      headers: {
        'Accept': 'application/vnd.github.v3+json',
        'Authorization': `Bearer ${GITHUB_PAT}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        ref: 'main' // Branch to run the workflow on
      })
    });

    if (!response.ok) {
      const errorData = await response.text();
      console.error('Trigger error:', errorData);
      return NextResponse.json({ error: 'Failed to trigger workflow from GitHub' }, { status: response.status });
    }

    return NextResponse.json({ message: 'Scraper triggered successfully!' });
  } catch (err: any) {
    console.error('Internal API error:', err);
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
