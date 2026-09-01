(()=>{const button=document.querySelector('#theme-toggle');if(!button)return;button.addEventListener('click',()=>{document.documentElement.classList.toggle('dark');localStorage.setItem('profile-theme',document.documentElement.classList.contains('dark')?'dark':'light')})})();

