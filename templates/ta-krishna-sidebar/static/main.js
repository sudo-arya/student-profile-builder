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
  const activate = id => {
    links.forEach(link => link.removeAttribute('aria-current'));
    links.get(id)?.setAttribute('aria-current', 'location');
  };
  const sections = [...document.querySelectorAll('.section-anchor')];
  const lastSection = sections.at(-1);
  const isPageEnd = () => {
    const page = document.documentElement;
    return window.scrollY + window.innerHeight >= page.scrollHeight - 12;
  };
  const activatePageEnd = () => {
    if (isPageEnd() && lastSection) activate(lastSection.id);
  };
  if ('IntersectionObserver' in window && links.size) {
    const observer = new IntersectionObserver(entries => {
      if (isPageEnd() && lastSection) {
        activate(lastSection.id);
        return;
      }
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        activate(entry.target.id);
      });
    }, {rootMargin: '-15% 0px -70% 0px', threshold: 0});
    sections.forEach(section => observer.observe(section));
  }
  addEventListener('scroll', activatePageEnd, {passive: true});
  addEventListener('resize', activatePageEnd);
  activatePageEnd();
})();
