fetch('./profile-data.json').then(response => response.json()).then(data => {
  document.querySelector('#name').textContent = data.profile.name;
  // content.html is builder-sanitized. Prefer DOM APIs for ordinary profile strings.
  document.querySelector('#content').innerHTML = data.content.html;
});
