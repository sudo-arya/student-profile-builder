const bar = document.querySelector('.site-bar');
const toggle = document.querySelector('[data-nav-toggle]');
const nav = document.querySelector('#site-nav');
if (bar && toggle && nav) {
  toggle.addEventListener('click', () => {
    const open = bar.classList.toggle('nav-open');
    toggle.setAttribute('aria-expanded', String(open));
  });
  nav.addEventListener('click', event => {
    if (event.target.closest('a')) { bar.classList.remove('nav-open'); toggle.setAttribute('aria-expanded', 'false'); }
  });
  nav.addEventListener('wheel', event => {
    if (getComputedStyle(nav).display === 'flex' && nav.scrollWidth > nav.clientWidth && Math.abs(event.deltaY) > Math.abs(event.deltaX)) {
      event.preventDefault();
      nav.scrollLeft += event.deltaY;
    }
  }, { passive: false });
}
const links = [...document.querySelectorAll('#site-nav a')];
const sections = links.map(link => document.querySelector(link.getAttribute('href'))).filter(Boolean);
if (sections.length && 'IntersectionObserver' in window) {
  const observer = new IntersectionObserver(entries => {
    const visible = entries.filter(entry => entry.isIntersecting).sort((a,b) => b.intersectionRatio-a.intersectionRatio)[0];
    if (!visible) return;
    links.forEach(link => link.toggleAttribute('aria-current', link.getAttribute('href') === `#${visible.target.id}`));
  }, { rootMargin: '-20% 0px -65%', threshold: [0, .25, .6] });
  sections.forEach(section => observer.observe(section));
}
