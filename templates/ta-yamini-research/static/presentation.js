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

  const about = document.querySelector('[data-section-type="about"] .section-body');
  if (about) {
    const quote = about.querySelector('blockquote');
    const narrative = document.createElement('div');
    [...about.children].filter(node => node !== quote).forEach(node => narrative.appendChild(node));
    about.prepend(narrative);
    if (quote) {
      quote.classList.add('pull');
      const side = document.createElement('div');
      side.appendChild(quote);
      about.appendChild(side);
    }
  }

  document.querySelectorAll('.career-body').forEach(career => {
    const section = career.closest('section[data-section-type]');
    const careerKind = section?.dataset.sectionType || 'education';
    const body = career.querySelector(':scope > .markdown-body');
    const entries = [...(body?.querySelectorAll('.semantic-entry') || [])];
    entries.forEach(entry => entry.dataset.careerKind = careerKind);
    if (body) body.remove();
    entries.forEach(entry => {
      entry.classList.add('rail-item');
      const heading = entry.querySelector(':scope > h2');
      const detail = entry.querySelector(':scope > p');
      const strong = detail?.querySelector('strong');
      if (heading && detail && strong) {
        let placeText = '';
        let periodText = '';
        if (entry.dataset.careerKind === 'education') {
          placeText = strong.textContent.trim();
          periodText = detail.textContent.replace(strong.textContent, '').trim();
        } else {
          const titleParts = heading.textContent.split(/\s+[—–]\s+/);
          if (titleParts.length > 1) {
            heading.textContent = titleParts.shift();
            placeText = titleParts.join(' — ').trim();
          }
          const detailParts = strong.textContent.split(/\s*·\s*/);
          if (detailParts.length > 1) {
            placeText = detailParts.shift().trim() || placeText;
            periodText = detailParts.join(' · ').trim();
          } else {
            periodText = strong.textContent.trim();
          }
        }
        const meta = document.createElement('p');
        meta.className = 'meta';
        meta.textContent = periodText;
        const place = document.createElement('p');
        place.className = 'place';
        place.textContent = placeText;
        detail.replaceWith(meta, place);
      }
      career.appendChild(entry);
    });
  });

  document.querySelectorAll('[data-section-type="research"] .semantic-entry').forEach(entry => {
    entry.classList.add('research-card');
    [...entry.querySelectorAll(':scope > p')].forEach(p => {
      const label = p.querySelector('strong');
      if (label && /^Methods:?$/i.test(label.textContent.trim())) p.classList.add('methods');
    });
  });

  const skills = document.querySelector('[data-section-type="skills"] .section-body');
  if (skills) {
    skills.classList.add('skills-grid');
    [...skills.children].filter(node => node.tagName === 'P').forEach(p => {
      const strong = p.querySelector('strong');
      if (!strong) return;
      const row = document.createElement('div');
      row.className = 'skill-row';
      const key = document.createElement('p');
      key.className = 'k';
      key.textContent = strong.textContent.replace(/:$/, '');
      strong.remove();
      const pills = document.createElement('div');
      pills.className = 'pill-row';
      p.textContent.split(',').map(value => value.trim().replace(/^and\s+/i, '')).filter(Boolean).forEach(value => {
        const pill = document.createElement('span');
        pill.className = 'pill';
        pill.textContent = value;
        pills.appendChild(pill);
      });
      row.append(key, pills);
      p.replaceWith(row);
    });
  }

  document.querySelectorAll('[data-section-type="projects"] .semantic-entry').forEach(entry => {
    entry.classList.add('project-card');
    const heading = entry.querySelector(':scope > h2');
    if (heading) {
      const parts = heading.textContent.split(/\s+[—–]\s+/);
      heading.textContent = parts.shift();
      if (parts.length) {
        const tagline = document.createElement('p');
        tagline.className = 'tagline';
        tagline.textContent = parts.join(' — ');
        heading.after(tagline);
      }
    }

    let bodyAssigned = false;
    [...entry.querySelectorAll(':scope > p')].forEach(p => {
      const strong = p.querySelector('strong');
      if (!strong || !/^Technologies:?$/i.test(strong.textContent.trim())) {
        if (!strong && !p.classList.contains('tagline') && !bodyAssigned) {
          p.classList.add('body');
          bodyAssigned = true;
        }
        return;
      }
      const values = splitList(textUntilBreak(strong));
      const links = [...p.querySelectorAll('a')].map(link => link.cloneNode(true));
      p.textContent = '';
      p.className = 'pill-row project-tech';
      values.forEach(value => {
        const pill = document.createElement('span');
        pill.className = 'pill pill-tight';
        pill.textContent = value;
        p.appendChild(pill);
      });
      if (links.length) {
        const linkRow = document.createElement('div');
        linkRow.className = 'proj-links';
        links.forEach(link => linkRow.appendChild(link));
        p.after(linkRow);
      }
    });
  });

  const teaching = document.querySelector('[data-section-type="teaching"] .section-body');
  if (teaching) {
    const mentoringHeading = [...teaching.querySelectorAll(':scope > h3')].find(node => /^Mentoring$/i.test(node.textContent.trim()));
    if (mentoringHeading) mentoringHeading.remove();
    const mentoring = teaching.querySelector(':scope > ul');
    if (mentoring) mentoring.classList.add('mentor-list');
  }

  const awards = document.querySelector('[data-section-type="awards"] .section-body');
  if (awards) {
    const list = awards.querySelector('ul');
    if (list) {
      list.className = 'simple-list';
      [...list.children].forEach(li => {
        li.className = 'simple-item';
        const strong = li.querySelector('strong');
        const title = strong ? strong.textContent : li.textContent;
        let rest = li.textContent.replace(title, '').replace(/^\s*,?\s*/, '');
        const periodMatch = rest.match(/(?:19|20)\d{2}(?:\s*[—–-]\s*(?:Present|(?:19|20)\d{2}))?$/i);
        const periodText = periodMatch?.[0] || '';
        if (periodText) rest = rest.slice(0, -periodText.length).replace(/[\s,]+$/, '');
        li.textContent = '';
        const info = document.createElement('div');
        const heading = document.createElement('p');
        heading.className = 't';
        heading.textContent = title;
        const place = document.createElement('p');
        place.className = 'p';
        place.textContent = rest;
        const period = document.createElement('span');
        period.className = 'period mono';
        period.textContent = periodText;
        info.append(heading, place);
        li.append(info, period);
      });
      const stats = document.getElementById('hero-stats');
      if (stats) {
        [...list.children].slice(0, 4).forEach(li => {
          const badge = document.createElement('div');
          badge.className = 'stat-badge';
          const headline = document.createElement('p');
          headline.className = 'headline';
          headline.textContent = (li.querySelector('.t')?.textContent || '').replace(/^Institute\s+/, '').replace(/^Best Student Paper\s+[—–]\s+/, '').replace(/^Graduate Research\s+/, '').replace(/^University\s+/, '');
          const caption = document.createElement('p');
          caption.className = 'caption';
          caption.textContent = [li.querySelector('.p')?.textContent, li.querySelector('.period')?.textContent].filter(Boolean).join(' · ');
          badge.append(headline, caption);
          stats.appendChild(badge);
        });
      }
    }
  }

  const service = document.querySelector('[data-section-type="service"] ul');
  if (service) service.classList.add('service-list');
  document.querySelectorAll('[data-section-type="talks"] .semantic-entry').forEach(entry => {
    entry.classList.add('talk-item');
    const detail = entry.querySelector(':scope > p');
    if (!detail) return;
    const match = detail.textContent.trim().match(/^(.*?)(?:,\s*)?((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})\.?$/i);
    if (!match) {
      detail.classList.add('venue');
      return;
    }
    detail.textContent = match[1].replace(/[\s,]+$/, '');
    detail.classList.add('venue');
    const period = document.createElement('span');
    period.className = 'period';
    period.textContent = match[2];
    detail.after(period);
  });

  const datasets = document.querySelector('#datasets .section-body');
  if (datasets) datasets.classList.add('research-card', 'dataset-card');

  const contact = document.querySelector('[data-section-type="contact"] .section-body');
  if (contact) {
    const lead = contact.querySelector(':scope > p:first-child');
    if (lead) lead.classList.add('lead');
    const source = [...contact.querySelectorAll(':scope > p')].find(p => p !== lead && p.querySelector('strong'));
    if (source) {
      const meta = document.createElement('div');
      meta.className = 'contact-meta';
      [...source.querySelectorAll('strong')].forEach(strong => {
        const item = document.createElement('div');
        const key = document.createElement('p');
        key.className = 'k';
        key.textContent = strong.textContent.replace(/:$/, '');
        const value = document.createElement('p');
        value.className = 'v';
        value.textContent = textUntilBreak(strong);
        item.append(key, value);
        meta.appendChild(item);
      });
      source.replaceWith(meta);
    }
  }
  const news = document.querySelector('[data-section-type="news"] ul');
  if (news) {
    news.classList.add('rail', 'news-rail');
    [...news.children].forEach(li => {
      li.classList.add('rail-item');
      const strong = li.querySelector('strong');
      if (!strong) return;
      const meta = document.createElement('p');
      meta.className = 'meta';
      meta.textContent = strong.textContent.replace(/:\s*$/, '');
      const body = document.createElement('p');
      body.className = 'news-body';
      while (strong.nextSibling) body.appendChild(strong.nextSibling);
      strong.remove();
      li.replaceChildren(meta, body);
    });
  }
})();
