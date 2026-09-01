async (page) => {
  const pages = [
    ["source", "http://127.0.0.1:8899/TA%20designs/Arya%20Singh/index.html"],
    ["generated", "http://127.0.0.1:8899/output/playwright/template-audit/ta-arya-editorial/index.html"]
  ];
  const viewports = [
    ["desktop", 1440, 1000],
    ["compact", 1024, 900],
    ["mobile", 390, 844]
  ];
  const results = {};
  for (const [viewport, width, height] of viewports) {
    await page.setViewportSize({ width, height });
    for (const [kind, url] of pages) {
      await page.goto(url, { waitUntil: "domcontentloaded", timeout: 15000 });
      await page.waitForTimeout(250);
      const key = `${kind}-${viewport}`;
      results[key] = await page.evaluate(() => {
        const box = selector => {
          const node = document.querySelector(selector);
          if (!node) return null;
          const rect = node.getBoundingClientRect();
          return { width: Math.round(rect.width), height: Math.round(rect.height), left: Math.round(rect.left) };
        };
        const cards = [...document.querySelectorAll("#projects article")].map(node => {
          const rect = node.getBoundingClientRect();
          return { width: Math.round(rect.width), height: Math.round(rect.height), top: Math.round(rect.top) };
        });
        return {
          documentWidth: document.documentElement.scrollWidth,
          viewportWidth: innerWidth,
          paper: box(".paper"),
          sidebar: box(".sidebar"),
          main: box("main"),
          projects: box("#projects"),
          projectBody: box("#projects .project-grid, #projects .has-entries"),
          cards
        };
      });
      await page.screenshot({ path: `arya/${key}-full.png`, fullPage: true });
      await page.locator("#projects").screenshot({ path: `arya/${key}-projects.png` });
    }
  }
  return results;
}
