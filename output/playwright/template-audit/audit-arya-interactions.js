async (page) => {
  const url = 'http://127.0.0.1:8899/output/playwright/template-audit/ta-arya-editorial/index.html';
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 15000 });
  await page.waitForTimeout(200);

  const normal = await page.evaluate(() => {
    const rows = [...document.querySelectorAll('#news .news > li')].map(row => {
      const date = row.querySelector('time').getBoundingClientRect();
      const copy = row.querySelector('.news-copy').getBoundingClientRect();
      return {
        date: row.querySelector('time').textContent.trim(),
        copy: row.querySelector('.news-copy').textContent.trim(),
        dateRight: Math.round(date.right),
        copyLeft: Math.round(copy.left),
        rowHeight: Math.round(row.getBoundingClientRect().height)
      };
    });
    const cards = [...document.querySelectorAll('#projects .semantic-entry')].map(card => ({
      background: getComputedStyle(card).backgroundColor,
      links: [...card.querySelectorAll('.project-actions a')].map(link => ({ text: link.textContent.trim(), href: link.href }))
    }));
    return { rows, cards };
  });
  await page.locator('#projects').screenshot({ path: 'arya/interactions-projects-normal.png' });
  await page.locator('#news').screenshot({ path: 'arya/interactions-news-desktop.png' });

  const firstCard = page.locator('#projects .semantic-entry').first();
  await firstCard.hover();
  await page.waitForTimeout(250);
  const hover = await firstCard.evaluate(card => ({
    transform: getComputedStyle(card).transform,
    borderColor: getComputedStyle(card).borderColor,
    shadow: getComputedStyle(card).boxShadow
  }));
  await page.locator('#projects').screenshot({ path: 'arya/interactions-projects-hover.png' });

  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 15000 });
  await page.waitForTimeout(200);
  const mobile = await page.evaluate(() => ({
    width: document.documentElement.scrollWidth,
    rows: [...document.querySelectorAll('#news .news > li')].map(row => ({
      dateTop: Math.round(row.querySelector('time').getBoundingClientRect().top),
      copyTop: Math.round(row.querySelector('.news-copy').getBoundingClientRect().top)
    }))
  }));
  await page.locator('#news').screenshot({ path: 'arya/interactions-news-mobile.png' });
  return { normal, hover, mobile };
}
