document.addEventListener('DOMContentLoaded', () => {
    // Tab Logic
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));

            btn.classList.add('active');
            const target = btn.getAttribute('data-target');
            document.getElementById(target).classList.add('active');

            if (target === 'issues-list' && !btn.dataset.loaded) {
                fetchIssues();
                btn.dataset.loaded = 'true';
            }
        });
    });

    // GitHub API Integration
    async function fetchIssues() {
        const container = document.getElementById('github-issues-container');
        const repo = 'Funnykid7/dungeon-adventure-rpg';
        
        try {
            const response = await fetch(`https://api.github.com/repos/${repo}/issues?state=open`);
            if (!response.ok) throw new Error('Failed to fetch scrolls.');
            
            const issues = await response.json();
            const realIssues = issues.filter(i => !i.pull_request);

            container.innerHTML = '';

            if (realIssues.length === 0) {
                container.innerHTML = '<p style="text-align: center; color: var(--accent-cyan); padding: 40px;">The Bounty Board is currently clear. The dungeon is at peace...</p>';
                return;
            }

            realIssues.forEach(issue => {
                const entry = document.createElement('div');
                entry.className = 'issue-entry';
                
                const labels = issue.labels.map(l => 
                    `<span style="color: #${l.color}; border: 1px solid #${l.color}; font-size: 0.7rem; padding: 2px 8px; border-radius: 10px; margin-left: 10px; font-family: Inter;">${l.name}</span>`
                ).join('');

                entry.innerHTML = `
                    <a href="${issue.html_url}" target="_blank" class="issue-link">${issue.title} ${labels}</a>
                    <div class="issue-meta">Order #${issue.number} posted by ${issue.user.login}</div>
                `;
                container.appendChild(entry);
            });

        } catch (err) {
            container.innerHTML = `<p style="text-align: center; color: #ff0064; padding: 40px;">Error: ${err.message}</p>`;
        }
    }

    // Scroll Observer for Glows
    const glows = document.querySelectorAll('.ambient-glow');
    window.addEventListener('scroll', () => {
        const scrolled = window.scrollY;
        glows[0].style.transform = `translate(${scrolled * 0.1}px, ${scrolled * 0.05}px)`;
        glows[1].style.transform = `translate(-${scrolled * 0.1}px, -${scrolled * 0.05}px)`;
    });
});