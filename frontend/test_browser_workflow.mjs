import puppeteer from 'puppeteer-core';

const CHROME_PATH = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const BASE_URL = 'http://localhost:5173';

async function runTests() {
  console.log('🚀 Starting headless browser workflow verification...');
  const browser = await puppeteer.launch({
    executablePath: CHROME_PATH,
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu', '--window-size=1440,900']
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900 });

  const consoleErrors = [];
  const networkFailures = [];

  page.on('console', msg => {
    if (msg.type() === 'error') {
      consoleErrors.push({ url: page.url(), text: msg.text() });
    }
  });

  page.on('pageerror', err => {
    console.error(`💥 UNCAUGHT PAGE ERROR on ${page.url()}:`, err.message, err.stack);
  });

  page.on('requestfailed', req => {
    networkFailures.push({ url: req.url(), errorText: req.failure()?.errorText });
  });

  const routes = [
    { path: '/', name: 'Landing Page', expectedSelector: 'h1, .hero-title, button' },
    { path: '/dashboard', name: 'Dashboard', expectedSelector: 'h1, h2, .metric-card, .dashboard-container' },
    { path: '/datasets', name: 'Data Sources Page', expectedSelector: 'table, .dataset-card, button, h1, h2' },
    { path: '/matches', name: 'Match Queue Page', expectedSelector: 'table, .match-card, button, h1, h2' },
    { path: '/conflicts', name: 'Conflict Review Page', expectedSelector: 'table, .conflict-card, button, h1, h2' },
    { path: '/workspace', name: 'Harmonization Workspace', expectedSelector: '.workspace-container, button, #map, h1, h2' },
    { path: '/harmonized', name: 'Harmonized Results Page', expectedSelector: 'table, .results-container, button, h1, h2' },
    { path: '/explorer', name: 'GIS Explorer', expectedSelector: '#map, .map-container, .gis-container, button' },
    { path: '/reports', name: 'Reports & Analytics', expectedSelector: '.reports-container, table, button, h1, h2' },
  ];

  const results = [];

  for (const r of routes) {
    console.log(`\n--- Testing ${r.name} (${r.path}) ---`);
    const initialErrorsLen = consoleErrors.length;
    const initialNetLen = networkFailures.length;

    try {
      const response = await page.goto(`${BASE_URL}${r.path}`, { waitUntil: 'networkidle0', timeout: 15000 });
      const status = response ? response.status() : 'no response';

      // Allow async effects / API fetches to render
      await new Promise(res => setTimeout(res, 1000));

      const title = await page.title();
      const bodyText = await page.evaluate(() => document.body.innerText.slice(0, 300));

      const newErrors = consoleErrors.slice(initialErrorsLen);
      const newNetFails = networkFailures.slice(initialNetLen);

      console.log(`Status: ${status} | Title: "${title}"`);
      console.log(`Preview: ${bodyText.replace(/\n+/g, ' | ')}`);

      if (newErrors.length > 0) {
        console.warn(`⚠️ Console Errors on ${r.path}:`, newErrors);
      }
      if (newNetFails.length > 0) {
        console.warn(`⚠️ Network Failures on ${r.path}:`, newNetFails);
      }

      results.push({
        route: r.path,
        name: r.name,
        status: status === 200 ? 'PASS' : 'WARN',
        errors: newErrors,
        netFails: newNetFails
      });
    } catch (err) {
      console.error(`❌ Failed navigating to ${r.path}:`, err.message);
      results.push({
        route: r.path,
        name: r.name,
        status: 'FAIL',
        error: err.message
      });
    }
  }

  console.log('\n=========================================');
  console.log('🏁 BROWSER WORKFLOW VERIFICATION SUMMARY');
  console.log('=========================================');
  for (const res of results) {
    console.log(`${res.status === 'PASS' ? '✅' : '❌'} [${res.status}] ${res.name} (${res.route}) - Errors: ${res.errors?.length || 0}, NetFails: ${res.netFails?.length || 0}`);
  }

  await browser.close();
}

runTests().catch(console.error);
