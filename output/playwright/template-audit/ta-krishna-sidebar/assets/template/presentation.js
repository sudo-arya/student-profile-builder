(() => {
  const splitList = text => text.split(',').map(value => value.trim().replace(/^and\s+/i, '')).filter(Boolean);
  const textUntilBreak = strong => {
    let text = '';
    for (let node = strong.nextSibling; node; node = node.nextSibling) {
      if (node.nodeType === Node.ELEMENT_NODE && node.tagName === 'BR') break;
      if (node.nodeType === Node.ELEMENT_NODE && node.tagName === 'A') continue;
      text += node.textContent || '';
    }
    return text.replace(/^:\s*/, '').trim();
  };
  const pillRow = (values, className = 'tag-pills') => {
    const row = document.createElement('span');
    row.className = className;
    values.forEach(value => {
      const pill = document.createElement('span');
      pill.textContent = value;
      row.appendChild(pill);
    });
    return row;
  };

  document.querySelectorAll('[data-section-type="education"] .semantic-entry, [data-section-type="experience"] .semantic-entry').forEach(entry => {
    const heading = entry.querySelector(':scope > h2');
    if (!heading) return;
    const headingParts = heading.textContent.split(/\s+[—–]\s+/);
    heading.textContent = headingParts.shift();
    const headingPlace = headingParts.join(' — ');
    const detail = entry.querySelector(':scope > p');
    const strong = detail?.querySelector('strong');
    const strongText = strong?.textContent.trim() || '';
    let place = headingPlace;
    let period = '';
    if (strongText.includes('·')) {
      const parts = strongText.split('·').map(value => value.trim());
      period = parts.pop() || '';
      place = [headingPlace, parts.join(' · ')].filter(Boolean).join(' · ');
    } else {
      place = place || strongText;
      period = detail ? detail.textContent.replace(strongText, '').trim() : '';
    }
    const top = document.createElement('div');
    top.className = 'entry-top';
    const date = document.createElement('span');
    date.className = 'entry-period';
    date.textContent = period;
    heading.before(top);
    top.append(heading, date);
    if (place) {
      const placeNode = document.createElement('p');
      placeNode.className = 'entry-place';
      placeNode.textContent = place;
      top.after(placeNode);
    }
    if (detail) detail.remove();
  });

  document.querySelectorAll('[data-section-type="research"] .semantic-entry p, [data-section-type="projects"] .semantic-entry p').forEach(p => {
    const strong = p.querySelector('strong');
    if (!strong || !/^(Methods|Technologies):?$/i.test(strong.textContent.trim())) return;
    const label = strong.textContent.replace(/:$/, '');
    const values = splitList(textUntilBreak(strong));
    const links = [...p.querySelectorAll('a')].map(link => link.cloneNode(true));
    p.textContent = '';
    p.className = 'tag-line';
    const key = document.createElement('strong');
    key.textContent = label;
    p.append(key, pillRow(values));
    if (links.length) {
      const linkRow = document.createElement('div');
      linkRow.className = 'project-links';
      links.forEach(link => linkRow.appendChild(link));
      p.after(linkRow);
    }
  });
  document.querySelectorAll('[data-section-type="projects"] .semantic-entry > h2').forEach(h => {
    const parts = h.textContent.split(/\s+[—–]\s+/);
    if (parts.length < 2) return;
    h.textContent = parts.shift();
    const tagline = document.createElement('p');
    tagline.className = 'project-tagline';
    tagline.textContent = parts.join(' — ');
    h.after(tagline);
  });

  const skills = document.querySelector('[data-section-type="skills"] .markdown-body');
  if (skills) {
    skills.classList.add('skills-grid');
    [...skills.children].filter(node => node.tagName === 'P').forEach(p => {
      const strong = p.querySelector('strong');
      if (!strong) return;
      const label = document.createElement('h3');
      label.textContent = strong.textContent.replace(/:$/, '');
      strong.remove();
      const values = splitList(p.textContent);
      p.textContent = '';
      p.className = 'skill-group';
      p.append(label, pillRow(values, 'skill-pills'));
    });
  }
})();
