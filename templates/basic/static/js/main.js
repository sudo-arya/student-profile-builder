const controls = document.querySelectorAll('[data-theme-choice]');
if (controls.length) {
  const root = document.documentElement;
  const configured = root.dataset.theme || 'system';
  const stored = localStorage.getItem('profile-theme');
  const saved = ['light', 'dark', 'system'].includes(stored) ? stored : configured;
  const apply = value => {
    root.dataset.theme = value;
    controls.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.themeChoice === value)));
  };
  apply(saved);
  controls.forEach(button => button.addEventListener('click', () => {
    localStorage.setItem('profile-theme', button.dataset.themeChoice); apply(button.dataset.themeChoice);
  }));
}
