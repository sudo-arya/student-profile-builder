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
