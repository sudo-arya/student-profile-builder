# Template submission checklist

Phase 5 additions:

- [ ] Arbitrary ordered custom sections render and hidden sections do not
- [ ] No Publications, Projects, or Awards sections works
- [ ] Theme toggle appears only when enabled; Light/Dark/System remain readable
- [ ] Extra pages and nested pages use relative cross-page links

## Metadata

- [ ] Valid template ID; manifest ID matches directory
- [ ] Version, author, description, engine, and schema compatibility provided
- [ ] License and third-party assets/CDNs/fonts documented

## Functionality and optional data

- [ ] Name, designation, institute, email, profile photo, research interests, and Markdown displayed
- [ ] Works without GitHub, LinkedIn, Scholar, website, CV, or profile photo
- [ ] Empty optional sections do not leave broken links or layout gaps

## Content and responsive tests

- [ ] Long student/institute names, many interests/publications, special characters, and Indian Unicode names
- [ ] Portrait and landscape images
- [ ] Desktop, tablet, and mobile
- [ ] Modern Chrome, Edge, Firefox, and Safari
- [ ] Semantic HTML, alt text, keyboard use, visible focus, headings, labels, and sufficient contrast

## Deployment and performance

- [ ] `index.html` generated; all runtime files are inside output
- [ ] Relative URLs only; works at an arbitrary subdirectory
- [ ] No local filesystem paths and no backend dependency
- [ ] Images optimized; no unnecessary large bundles/libraries or autoplay background video

## Security and submission

- [ ] User strings inserted safely; no arbitrary unsanitized `innerHTML` or `eval`
- [ ] No credentials, API secrets, authentication, silent forms, or unapproved tracking
- [ ] `template-check` passes with minimal, full, and stress profiles
- [ ] Submission contains only the template directory and its required documentation/build files
