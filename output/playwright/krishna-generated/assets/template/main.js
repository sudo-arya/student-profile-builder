(() => {
  const root = document.documentElement;
  const button = document.querySelector('#theme-toggle');
  const icon = document.querySelector('#theme-icon');
  const paintThemeControl = () => {
    if (!button || !icon) return;
    const dark = root.classList.contains('dark');
    icon.textContent = dark ? '☀️' : '🌙';
    const label = dark ? 'Switch to light mode' : 'Switch to dark mode';
    button.setAttribute('aria-label', label);
    button.title = label;
  };
  paintThemeControl();
  button?.addEventListener('click', () => {
    root.classList.toggle('dark');
    localStorage.setItem('profile-theme', root.classList.contains('dark') ? 'dark' : 'light');
    paintThemeControl();
  });

  const links = new Map([...document.querySelectorAll('.section-nav a')].map(link =>
    [decodeURIComponent(link.hash.slice(1)), link]
  ));
  if ('IntersectionObserver' in window && links.size) {
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        links.forEach(link => link.removeAttribute('aria-current'));
        links.get(entry.target.id)?.setAttribute('aria-current', 'location');
      });
    }, {rootMargin: '-15% 0px -70% 0px', threshold: 0});
    document.querySelectorAll('.section-anchor').forEach(section => observer.observe(section));
  }
})();
