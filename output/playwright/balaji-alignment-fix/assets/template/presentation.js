(() => {
  const projectSection = document.querySelector('[data-section-type="projects"]');
  if (!projectSection) return;

  const splitProjectTitle = (heading) => {
    const parts = heading.textContent.trim().split(/\s+[—–]\s+/, 2);
    if (parts.length !== 2) return;
    heading.textContent = parts[0];
    const subtitle = document.createElement('p');
    subtitle.className = 'project-subtitle';
    subtitle.textContent = parts[1];
    heading.after(subtitle);
  };

  const technologyNames = (paragraph) => {
    const copy = paragraph.cloneNode(true);
    copy.querySelectorAll('a,strong').forEach((node) => node.remove());
    return copy.textContent
      .replace(/^\s*:?\s*/, '')
      .split(/,|\band\b/i)
      .map((name) => name.replace(/[·•]\s*$/, '').trim())
      .filter(Boolean);
  };

  projectSection.querySelectorAll('.semantic-entry').forEach((card) => {
    card.classList.add('project-card');
    card.tabIndex = 0;

    const heading = card.querySelector(':scope > h2');
    if (heading) splitProjectTitle(heading);

    const paragraphs = [...card.querySelectorAll(':scope > p')];
    const description = paragraphs.find((paragraph) => !paragraph.querySelector('strong'));
    if (description) description.classList.add('project-description');

    const details = paragraphs.find((paragraph) =>
      paragraph.querySelector('strong')?.textContent.trim().toLowerCase().startsWith('technologies')
    );
    if (!details) return;

    const names = technologyNames(details);
    if (names.length) {
      const technologies = document.createElement('div');
      technologies.className = 'project-technologies';
      technologies.setAttribute('aria-label', 'Technologies');
      names.forEach((name) => {
        const chip = document.createElement('span');
        chip.textContent = name;
        technologies.appendChild(chip);
      });
      details.before(technologies);
    }

    const links = [...details.querySelectorAll('a')];
    if (links.length) {
      const actions = document.createElement('div');
      actions.className = 'project-actions';
      links.forEach((link, index) => {
        const action = link.cloneNode(true);
        action.classList.add(index === 0 ? 'primary-action' : 'secondary-action');
        action.target = '_blank';
        action.rel = 'noopener noreferrer';
        actions.appendChild(action);
      });
      details.before(actions);
    }
    details.remove();
  });
})();

(() => {
  const table = document.querySelector('[data-section-type="teaching"] table');
  if (!table) return;

  table.classList.add('teaching-table');
  table.querySelectorAll('tbody tr').forEach((row) => {
    row.tabIndex = 0;
    const cells = row.querySelectorAll('td');
    [[cells[0], 'teaching-term'], [cells[2], 'teaching-role']].forEach(([cell, className]) => {
      if (!cell || !cell.textContent.trim()) return;
      const value = document.createElement('span');
      value.className = className;
      value.textContent = cell.textContent.trim();
      cell.replaceChildren(value);
    });
  });
})();
