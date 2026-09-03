const control = document.querySelector('[data-theme-toggle]');
if (control) {
  const root = document.documentElement;
  const configured = root.dataset.theme || 'system';
  const stored = localStorage.getItem('profile-theme');
  const saved = ['light', 'dark', 'system'].includes(stored) ? stored : configured;
  const apply = value => {
    root.dataset.theme = value;
    const dark = value === 'dark' || (value === 'system' && matchMedia('(prefers-color-scheme: dark)').matches);
    control.querySelector('span').textContent = dark ? '☀' : '☾';
    control.setAttribute('aria-label', dark ? 'Switch to light theme' : 'Switch to dark theme');
    control.title = control.getAttribute('aria-label');
  };
  apply(saved);
  control.addEventListener('click', () => {
    const dark = root.dataset.theme === 'dark' || (root.dataset.theme === 'system' && matchMedia('(prefers-color-scheme: dark)').matches);
    const next = dark ? 'light' : 'dark'; localStorage.setItem('profile-theme', next); apply(next);
  });
}

document.querySelectorAll('[data-section-type="skills"] .section-body p').forEach(paragraph => {
  const label = paragraph.querySelector(':scope > strong');
  if (!label) return;
  const value = paragraph.textContent.slice(label.textContent.length).replace(/^\s*:\s*/, '');
  const items = value.split(',').map(item => item.trim().replace(/^and\s+/i, '')).filter(Boolean);
  if (!items.length) return;
  const group = document.createElement('div');
  group.className = 'skill-group';
  const heading = document.createElement('strong');
  heading.className = 'skill-label';
  heading.textContent = label.textContent.replace(/:\s*$/, '');
  const pills = document.createElement('span');
  pills.className = 'skill-pills';
  items.forEach(item => {
    const pill = document.createElement('span');
    pill.className = 'skill-pill';
    pill.textContent = item;
    pills.appendChild(pill);
  });
  group.append(heading, pills);
  paragraph.replaceWith(group);
});

document.querySelectorAll('[data-section-type="projects"] .section-body a, [data-section-type="custom"] .section-body a').forEach(link => link.classList.add('content-action'));
