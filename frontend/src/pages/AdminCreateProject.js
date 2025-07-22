import React, { useState, useEffect } from 'react'

const PUBLIC_BASE_URL = 'https://basilisk-exact-fully.ngrok-free.app'

function AdminCreateProject() {
  const [userData, setUserData] = useState(null)
  const [name, setName] = useState('')
  const [status, setStatus] = useState('')
  const [isCreating, setIsCreating] = useState(false)

  useEffect(() => {
    const raw = localStorage.getItem('user')
    if (raw) setUserData(JSON.parse(raw))
  }, [])

  const createGitHubRepo = async (projectName, githubToken) => {
    const res = await fetch('https://api.github.com/user/repos', {
      method: 'POST',
      headers: {
        Authorization: `token ${githubToken}`,
        'Content-Type': 'application/json',
        Accept: 'application/vnd.github.v3+json'
      },
      body: JSON.stringify({
        name: projectName,
        description: `Project repository for ${projectName}`,
        private: false,
        auto_init: true,
        has_issues: true,
        has_projects: true,
        has_wiki: true
      })
    })
    const text = await res.text()
    if (!res.ok) throw new Error(text || 'GitHub repo creation failed')
    return JSON.parse(text)
  }

  const createWebhook = async (projectName, githubUsername, githubToken, webhookUrl) => {
    const res = await fetch(`https://api.github.com/repos/${githubUsername}/${projectName}/hooks`, {
      method: 'POST',
      headers: {
        Authorization: `token ${githubToken}`,
        'Content-Type': 'application/json',
        Accept: 'application/vnd.github.v3+json'
      },
      body: JSON.stringify({
        name: 'web',
        active: true,
        events: ['push', 'pull_request', 'issues'],
        config: { url: webhookUrl, content_type: 'json', insecure_ssl: '0' }
      })
    })
    const text = await res.text()
    if (!res.ok) throw new Error(text || 'Webhook creation failed')
    return JSON.parse(text)
  }

 const protectMainBranch = async (projectName, githubUsername, githubToken) => {
  const protectionUrl = `https://api.github.com/repos/${githubUsername}/${projectName}/branches/main/protection`;

  const res = await fetch(protectionUrl, {
    method: 'PUT',
    headers: {
      Authorization: `token ${githubToken}`,
      'Content-Type': 'application/json',
      Accept: 'application/vnd.github+json',
    },
    body: JSON.stringify({
      required_status_checks: null, // No status checks required
      enforce_admins: true, // Enforce protection for admins
      required_pull_request_reviews: {
        dismiss_stale_reviews: false, // Don’t dismiss stale reviews
        require_code_owner_reviews: false, // No code owner reviews required
        required_approving_review_count: 1, // Require 1 approval
      },
      restrictions: null, // Explicitly null for personal repos
    }),
  });

  const text = await res.text();
  if (!res.ok) throw new Error(text || 'Branch protection failed');
  return JSON.parse(text);
};


  const handleCreate = async () => {
    if (!userData || !userData.githubUsername) {
      setStatus('Admin GitHub username missing')
      return
    }
    if (!userData.githubToken) {
      setStatus('GitHub token missing')
      return
    }
    if (!name.trim()) {
      setStatus('Project name required')
      return
    }
    setIsCreating(true)
    setStatus('Creating project')
    try {
      const projectRes = await fetch('http://localhost:5001/admin/create_project', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: name.trim(),
          adminGithubUsername: userData.githubUsername,
          createdAt: new Date().toISOString()
        })
      })
      const projData = await projectRes.json()
      if (!projectRes.ok) throw new Error(projData.error || 'Project create failed')
      setStatus('Creating repository')
      const repoData = await createGitHubRepo(name.trim(), userData.githubToken)
      setStatus('Creating webhook')
const webhookUrl = `${PUBLIC_BASE_URL}/webhooks/github/${name.trim()}`
const webhookData = await createWebhook(name.trim(), userData.githubUsername, userData.githubToken, webhookUrl)

// ➕ NEW STEP: Protect main branch after webhook is created
setStatus('Protecting main branch (only PRs allowed)')
await protectMainBranch(name.trim(), userData.githubUsername, userData.githubToken)

await fetch('http://localhost:5001/admin/update_project', {
  method: 'PUT',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    name: name.trim(),
    githubRepoUrl: repoData.html_url,
    githubRepoId: repoData.id,
    webhookId: webhookData.id,
    webhookUrl: webhookUrl
  })
})
      setStatus(`Project "${name.trim()}" created`)
      setName('')
    } catch (err) {
      setStatus(err.message)
    } finally {
      setIsCreating(false)
    }
  }

  if (!userData) {
    return <div style={{ padding: 20 }}>Loading user data</div>
  }

  return (
    <div style={{ padding: 20 }}>
      <h2>Create New Project</h2>
      <input
        style={{ width: '100%', padding: 10, marginBottom: 15, border: '1px solid #ccc', borderRadius: 4 }}
        disabled={isCreating}
        value={name}
        onChange={e => setName(e.target.value)}
        placeholder="Project name"
      />
      <button
        disabled={isCreating || !name.trim()}
        onClick={handleCreate}
        style={{
          padding: '10px 20px',
          background: isCreating ? '#ccc' : '#007bff',
          color: 'white',
          border: 'none',
          borderRadius: 4
        }}
      >
        {isCreating ? 'Creating…' : 'Create Project & Repo'}
      </button>
      {status && <div style={{ marginTop: 20 }}>{status}</div>}
    </div>
  )
}

export default AdminCreateProject
