async (page) => {
  await page.setViewportSize({ width: 390, height: 844 });
  for (const [name, url] of [
    ["arya", "http://127.0.0.1:8899/output/playwright/template-audit/ta-arya-editorial/index.html"],
    ["balaji", "http://127.0.0.1:8899/output/playwright/template-audit/ta-balaji-tailwind/index.html"],
    ["krishna", "http://127.0.0.1:8899/output/playwright/template-audit/ta-krishna-sidebar/index.html"],
    ["yamini", "http://127.0.0.1:8899/output/playwright/template-audit/ta-yamini-research/index.html"]
  ]) {
    await page.goto(url, { waitUntil: "domcontentloaded", timeout: 15000 });
    await page.waitForTimeout(300);
    const width = await page.evaluate(() => document.documentElement.scrollWidth);
    if (width > 390) throw new Error(`${name} horizontally overflows at ${width}px`);
    await page.screenshot({ path: `screenshots/${name}-generated-mobile.png`, fullPage: true });
  }
}
