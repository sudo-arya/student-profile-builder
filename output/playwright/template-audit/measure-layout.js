async (page) => {
  const pages = [
    ["yamini-source", "http://127.0.0.1:8899/TA%20designs/Yamini%20Chandana/dist/index.html"],
    ["yamini-generated", "http://127.0.0.1:8899/output/playwright/template-audit/ta-yamini-research/index.html"],
    ["krishna-source", "http://127.0.0.1:8899/TA%20designs/Krishna%20Bisht/student.html"],
    ["krishna-generated", "http://127.0.0.1:8899/output/playwright/template-audit/ta-krishna-sidebar/index.html"],
    ["balaji-source", "http://127.0.0.1:8899/TA%20designs/Athinagaram%20Shree%20Balaji/Student%20website%20static%20sample.html"],
    ["balaji-generated", "http://127.0.0.1:8899/output/playwright/template-audit/ta-balaji-tailwind/index.html"]
  ];
  const selectors = {
    "yamini-source": { teaching: "#teaching", projects: "#projects", skills: "#skills" },
    "yamini-generated": { teaching: "[data-section-type=teaching]", projects: "[data-section-type=projects]", skills: "[data-section-type=skills]" },
    "krishna-source": { teaching: "#teaching", projects: "#projects", skills: "#skills" },
    "krishna-generated": { teaching: "[data-section-type=teaching]", projects: "[data-section-type=projects]", skills: "[data-section-type=skills]" },
    "balaji-source": { teaching: "#teaching", projects: "#projects", skills: "#skills" },
    "balaji-generated": { teaching: "[data-section-type=teaching]", projects: "[data-section-type=projects]", skills: "[data-section-type=skills]" }
  };
  const results = {};
  await page.setViewportSize({ width: 1920, height: 1200 });
  for (const [name, url] of pages) {
    await page.goto(url, { waitUntil: "domcontentloaded", timeout: 15000 });
    await page.waitForTimeout(500);
    if (name === "yamini-source") {
      await page.locator("[data-reveal]").evaluateAll(nodes => nodes.forEach(node => node.classList.add("visible")));
    }
    results[name] = await page.evaluate(({ name, selectors }) => {
      const rect = node => {
        if (!node) return null;
        const box = node.getBoundingClientRect();
        return { width: Math.round(box.width), height: Math.round(box.height), top: Math.round(box.top) };
      };
      const section = key => document.querySelector(selectors[name][key]);
      const teaching = section("teaching");
      const projects = section("projects");
      const skills = section("skills");
      const table = teaching?.querySelector("table");
      const tableHost = table?.parentElement;
      const projectCards = [...(projects?.querySelectorAll(".project-card, .semantic-entry") || [])];
      const projectLinks = [...(projects?.querySelectorAll("a") || [])].map(link => link.textContent.trim());
      const technologyText = [...(projects?.querySelectorAll(".tech, .tag-line, .tag-pills, .pill-row") || [])].map(node => node.textContent.trim());
      const skillPills = [...(skills?.querySelectorAll(".pill, .skill-pills > span") || [])].map(node => node.textContent.trim());
      return {
        teaching: rect(teaching),
        table: rect(table),
        tableHost: rect(tableHost),
        tableFill: table && tableHost ? Number((table.getBoundingClientRect().width / tableHost.getBoundingClientRect().width).toFixed(3)) : null,
        projects: rect(projects),
        projectCards: projectCards.map(rect),
        projectLinks,
        technologyText,
        skillPills,
        sectionPadding: teaching ? getComputedStyle(teaching).padding : null
      };
    }, { name, selectors });
    for (const key of ["projects", "teaching", "skills"]) {
      const locator = page.locator(selectors[name][key]).first();
      if (await locator.count()) await locator.screenshot({ path: `focused/${name}-${key}.png` });
    }
  }
  return results;
}
