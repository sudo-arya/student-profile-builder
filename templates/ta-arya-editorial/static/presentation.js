(() => {
  const projectKinds = ['open source', 'prototype', 'benchmark'];
  document.querySelectorAll('[data-section-type="projects"] .semantic-entry').forEach((entry, index) => {
    const heading = entry.querySelector(':scope > h2');
    if (!heading) return;
    entry.tabIndex = 0;
    const tag = document.createElement('span');
    tag.className = 'project-tag';
    tag.textContent = `${String(index + 1).padStart(2, '0')} / ${projectKinds[index] || 'project'}`;
    heading.before(tag);

    const links = [...entry.querySelectorAll(':scope > p a')];
    if (links.length) {
      const source = links[0].parentElement;
      const actions = document.createElement('div');
      actions.className = 'project-actions';
      links.forEach(link => {
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        actions.appendChild(link);
      });
      [...source.childNodes].forEach(node => {
        if (node.nodeType === Node.ELEMENT_NODE && node.tagName === 'BR') node.remove();
        if (node.nodeType === Node.TEXT_NODE && /^[\s·]+$/.test(node.textContent)) node.remove();
      });
      entry.appendChild(actions);
    }
  });

  document.querySelectorAll('[data-section-type="research"] .semantic-entry').forEach(entry => {
    entry.tabIndex = 0;
  });

  const publications = document.querySelector('[data-section-type="publications"] .markdown-body');
  if (publications) {
    const list = publications.querySelector(':scope > ol');
    if (list) list.classList.add('pubs');
    [...publications.querySelectorAll(':scope > p')].forEach(p => {
      if (/fictional|template development/i.test(p.textContent)) p.classList.add('note');
    });
  }

  const awards = document.querySelector('[data-section-type="awards"] .markdown-body > ul');
  if (awards) awards.classList.add('award-list');

  const news = document.querySelector('[data-section-type="news"] .markdown-body > ul');
  if (news) {
    news.classList.add('news');
    [...news.querySelectorAll(':scope > li > ul > li')].forEach(item => news.appendChild(item));
    news.querySelectorAll(':scope > li > ul').forEach(list => list.remove());
    [...news.children].forEach(item => {
      const date = item.querySelector(':scope > strong');
      if (!date) return;
      const time = document.createElement('time');
      time.textContent = date.textContent.replace(/:\s*$/, '').trim();
      date.replaceWith(time);
      const copy = document.createElement('span');
      copy.className = 'news-copy';
      while (time.nextSibling) copy.appendChild(time.nextSibling);
      item.appendChild(copy);
    });
  }

  const datasets = document.querySelector('[data-section-type="datasets"] .markdown-body');
  if (datasets && datasets.querySelector(':scope > h2')) {
    const resource = document.createElement('article');
    resource.className = 'resource';
    resource.tabIndex = 0;
    while (datasets.firstChild) resource.appendChild(datasets.firstChild);
    datasets.appendChild(resource);
  }
})();
