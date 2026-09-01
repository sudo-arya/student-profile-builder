async (page) => {
  const pairs = [
    ["arya", "http://127.0.0.1:8899/TA%20designs/Arya%20Singh/index.html", "http://127.0.0.1:8899/output/playwright/template-audit/ta-arya-editorial/index.html"],
    ["balaji", "http://127.0.0.1:8899/TA%20designs/Athinagaram%20Shree%20Balaji/Student%20website%20static%20sample.html", "http://127.0.0.1:8899/output/playwright/template-audit/ta-balaji-tailwind/index.html"],
    ["krishna", "http://127.0.0.1:8899/TA%20designs/Krishna%20Bisht/student.html", "http://127.0.0.1:8899/output/playwright/template-audit/ta-krishna-sidebar/index.html"],
    ["yamini", "http://127.0.0.1:8899/TA%20designs/Yamini%20Chandana/dist/index.html", "http://127.0.0.1:8899/output/playwright/template-audit/ta-yamini-research/index.html"]
  ];
  const viewports = [["desktop", 1440, 1000], ["mobile", 390, 844]];
  for (const [label, width, height] of viewports) {
    await page.setViewportSize({ width, height });
    for (const [name, source, generated] of pairs) {
      for (const [kind, url] of [["source", source], ["generated", generated]]) {
        await page.goto(url, { waitUntil: "domcontentloaded", timeout: 15000 });
        await page.waitForTimeout(500);
        if (name === "yamini" && kind === "source") {
          await page.locator("[data-reveal]").evaluateAll(nodes => nodes.forEach(node => node.classList.add("visible")));
        }
        await page.screenshot({ path: `screenshots/${name}-${kind}-${label}.png`, fullPage: true });
      }
    }
  }
}
