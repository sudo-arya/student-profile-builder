(() => {
  const line = (body) => ({
    viewBox: '0 0 24 24', body,
    attrs: 'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"'
  });
  const fill = (viewBox, body) => ({viewBox, body, attrs: 'fill="currentColor"'});
  const icons = {
    moon: line('<path d="M20.5 14.2A8.5 8.5 0 0 1 9.8 3.5 8.5 8.5 0 1 0 20.5 14.2Z"/>'),
    sun: line('<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>'),
    menu: line('<path d="M4 7h16M4 12h16M4 17h16"/>'),
    close: line('<path d="m6 6 12 12M18 6 6 18"/>'),
    email: line('<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/>'),
    github: fill('0 0 16 16','<path d="M8 0a8 8 0 0 0-2.53 15.59c.4.07.55-.17.55-.38v-1.49c-2.23.49-2.7-1.08-2.7-1.08-.37-.93-.9-1.18-.9-1.18-.73-.5.06-.49.06-.49.8.06 1.23.83 1.23.83.72 1.23 1.88.87 2.34.67.07-.52.28-.87.51-1.07-1.78-.2-3.65-.89-3.65-3.96 0-.88.31-1.59.83-2.15-.08-.2-.36-1.02.08-2.12 0 0 .68-.22 2.2.82A7.7 7.7 0 0 1 8 3.72c.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.52.56.83 1.27.83 2.15 0 3.08-1.87 3.75-3.66 3.95.29.25.55.74.55 1.5v2.32c0 .21.14.46.55.38A8 8 0 0 0 8 0Z"/>'),
    linkedin: fill('0 0 16 16','<path d="M0 1.15C0 .52.53 0 1.18 0h13.64C15.47 0 16 .52 16 1.15v13.7c0 .63-.53 1.15-1.18 1.15H1.18C.53 16 0 15.48 0 14.85V1.15Zm4.94 12.24V6.17H2.54v7.22h2.4ZM3.74 5.18c.84 0 1.36-.56 1.36-1.25-.02-.71-.52-1.25-1.34-1.25-.82 0-1.36.54-1.36 1.25 0 .69.52 1.25 1.31 1.25h.03Zm2.53 8.21h2.4V9.36c0-.22.02-.43.08-.59.17-.43.56-.88 1.22-.88.86 0 1.2.66 1.2 1.62v3.88h2.4V9.23c0-2.23-1.19-3.27-2.78-3.27-1.3 0-1.87.72-2.19 1.22h.02V6.17H6.27c.03.67 0 7.22 0 7.22Z"/>'),
    scholar: line('<path d="m3 10 9-5 9 5-9 5-9-5Z"/><path d="M7 12.5V17c3 2.2 7 2.2 10 0v-4.5M21 10v6"/>'),
    globe: line('<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3.2 3 14.8 0 18M12 3c-3 3.2-3 14.8 0 18"/>'),
    file: line('<path d="M6 3h8l4 4v14H6V3Z"/><path d="M14 3v5h5M9 13h6M9 17h6"/>'),
    user: line('<circle cx="12" cy="8" r="4"/><path d="M4.5 21a7.5 7.5 0 0 1 15 0"/>'),
    news: line('<path d="M4 5h13v15H4zM17 8h3v10a2 2 0 0 1-2 2h-1"/><path d="M7 9h7M7 13h7M7 17h4"/>'),
    research: line('<path d="m10 3 4 4-3 3-4-4 3-3ZM11 10l-5 5M14 13a5 5 0 0 1 5 5M5 21h14M8 18h8"/>'),
    book: line('<path d="M4 5a3 3 0 0 1 3-2h5v17H7a3 3 0 0 0-3 2V5ZM20 5a3 3 0 0 0-3-2h-5v17h5a3 3 0 0 1 3 2V5Z"/>'),
    laptop: line('<rect x="4" y="4" width="16" height="12" rx="1"/><path d="M2 20h20M10 8l-2 2 2 2M14 8l2 2-2 2"/>'),
    briefcase: line('<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M8 7V4h8v3M3 12h18M10 12v2h4v-2"/>'),
    teaching: line('<path d="M4 4h16v11H4zM8 20l4-5 4 5M2 4h20"/><path d="M8 9h3M14 8v3"/>'),
    code: line('<path d="m8 9-3 3 3 3M16 9l3 3-3 3M14 6l-4 12"/>'),
    trophy: line('<path d="M8 4h8v4a4 4 0 0 1-8 0V4ZM9 20h6M12 12v8M8 6H4v2a4 4 0 0 0 4 4M16 6h4v2a4 4 0 0 1-4 4"/>'),
    database: line('<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/>'),
    link: line('<path d="M10 13a5 5 0 0 0 7.5.5l2-2a5 5 0 0 0-7-7l-1.1 1.1M14 11a5 5 0 0 0-7.5-.5l-2 2a5 5 0 0 0 7 7l1.1-1.1"/>')
  };

  const makeIcon = (name, className = '') => {
    const definition = icons[name];
    if (!definition) return null;
    const wrapper = document.createElement('span');
    wrapper.className = `ui-icon ${className}`.trim();
    wrapper.setAttribute('aria-hidden', 'true');
    wrapper.innerHTML = `<svg viewBox="${definition.viewBox}" ${definition.attrs}>${definition.body}</svg>`;
    return wrapper;
  };
  const prependIcon = (element, name, className = '') => {
    if (!element || element.querySelector(':scope > .ui-icon')) return;
    const icon = makeIcon(name, className);
    if (icon) {
      element.classList.add('has-ui-icon');
      element.prepend(icon);
    }
  };

  const sectionIcon = (section) => {
    const heading = section.querySelector(':scope > h2, :scope > h3');
    const identity = `${section.dataset.sectionType || ''} ${section.id || ''} ${heading?.textContent || ''}`.toLowerCase();
    const matches = [
      ['about','user'], ['news','news'], ['research','research'], ['publication','book'],
      ['project','laptop'], ['education','scholar'], ['experience','briefcase'],
      ['teaching','teaching'], ['skill','code'], ['award','trophy']
    ];
    return {heading, name: matches.find(([term]) => identity.includes(term))?.[1]};
  };
  document.querySelectorAll('section[data-section-type]').forEach((section) => {
    const {heading, name} = sectionIcon(section);
    if (name) prependIcon(heading, name, 'section-icon');
  });

  const iconForLink = (link) => {
    const identity = `${link.textContent} ${link.getAttribute('href') || ''}`.toLowerCase();
    if (identity.includes('github') || identity.includes('source code')) return 'github';
    if (identity.includes('linkedin')) return 'linkedin';
    if (identity.includes('scholar')) return 'scholar';
    if (identity.includes('resume') || identity.includes('preprint') || identity.includes('paper')) return 'file';
    if (identity.includes('email') || identity.includes('mailto:')) return 'email';
    if (identity.includes('dataset')) return 'database';
    if (identity.includes('documentation') || identity.includes('docs')) return 'book';
    if (identity.includes('code')) return 'code';
    if (identity.includes('doi')) return 'link';
    if (identity.includes('website') || identity.includes('project page') || identity.includes(' page')) return 'globe';
    return null;
  };
  document.querySelectorAll('.profile-links a,[data-section-type="publications"] a,[data-section-type="projects"] a,.dataset-panel a,.footer-email,.footer-bottom a').forEach((link) => {
    const name = iconForLink(link);
    if (name) prependIcon(link, name, 'link-icon');
  });

  const root = document.documentElement;
  const themeToggle = document.querySelector('#theme-toggle');
  const menuToggle = document.querySelector('#menu-toggle');
  const menu = document.querySelector('#mobile-menu');
  const renderControl = (button, name) => {
    if (!button) return;
    button.classList.add('has-ui-icon', 'icon-only');
    button.replaceChildren(makeIcon(name, 'control-icon'));
  };
  const renderTheme = () => renderControl(themeToggle, root.classList.contains('dark') ? 'sun' : 'moon');
  const renderMenu = () => renderControl(menuToggle, menu?.classList.contains('hidden') ? 'menu' : 'close');
  renderTheme(); renderMenu();
  themeToggle?.addEventListener('click', renderTheme);
  menuToggle?.addEventListener('click', renderMenu);
})();
