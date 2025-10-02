(function(){
  function resolveFromScript(relative){
    var script = document.currentScript || (function(){var s=document.getElementsByTagName("script");return s[s.length-1];})();
    try { return new URL(relative, script.src).toString(); } catch(e){ return relative; }
  }

  class SiteHeader extends HTMLElement{
    constructor(){ super(); this.attachShadow({mode:'open'}); }
    async connectedCallback(){
      const root = this.shadowRoot;
      const wrap = document.createElement('div');
      wrap.className = 'header';
      const cssUrl = resolveFromScript('../css/header.css');
      const htmlUrl = resolveFromScript((location.pathname.indexOf('/views/') !== -1 || location.pathname.indexOf('\\\\views\\\\') !== -1) ? '../components/header.views.html' : '../components/header.html');
      const [cssText, htmlText] = await Promise.all([
        fetch(cssUrl).then(r=>r.text()),
        fetch(htmlUrl).then(r=>r.text())
      ]);
      const style = document.createElement('style');
      style.textContent = cssText;
      wrap.innerHTML = htmlText;
      root.appendChild(style);
      root.appendChild(wrap);

      const headerEl = wrap;
      function setHeaderHeight(){
        const h = headerEl.offsetHeight || 100;
        document.documentElement.style.setProperty('--header-height', h + 'px');
      }
      function onScroll(){
        if(window.scrollY > 10){ headerEl.classList.add('scrolled'); } else { headerEl.classList.remove('scrolled'); }
        setHeaderHeight();
      }
      window.addEventListener('load', setHeaderHeight);
      window.addEventListener('resize', setHeaderHeight);
      window.addEventListener('scroll', onScroll);
      setHeaderHeight();

      // Countdown logic
      const targetDate = new Date('2025-11-15T00:00:00').getTime();
      function updateCountdown(){
        const now = Date.now();
        const d = targetDate - now;
        const days = Math.max(0, Math.floor(d / (1000*60*60*24)));
        const hours = Math.max(0, Math.floor((d % (1000*60*60*24)) / (1000*60*60)));
        const minutes = Math.max(0, Math.floor((d % (1000*60*60)) / (1000*60)));
        const seconds = Math.max(0, Math.floor((d % (1000*60)) / 1000));
        const rootQuery = (id)=> headerEl.querySelector('#'+id);
        var el;
        if((el=rootQuery('days'))){ el.textContent = String(days).padStart(2,'0'); }
        if((el=rootQuery('hours'))){ el.textContent = String(hours).padStart(2,'0'); }
        if((el=rootQuery('minutes'))){ el.textContent = String(minutes).padStart(2,'0'); }
        if((el=rootQuery('seconds'))){ el.textContent = String(seconds).padStart(2,'0'); }
      }
      updateCountdown();
      setInterval(updateCountdown, 1000);
    }
  }

  class SiteFooter extends HTMLElement{
    constructor(){ super(); this.attachShadow({mode:'open'}); }
    async connectedCallback(){
      const root = this.shadowRoot;
      const container = document.createElement('footer');
      container.className = 'footer';
      const cssUrl = resolveFromScript('../css/footer.css');
      const htmlUrl = resolveFromScript((location.pathname.indexOf('/views/') !== -1 || location.pathname.indexOf('\\\\views\\\\') !== -1) ? '../components/footer.views.html' : '../components/footer.html');
      const [cssText, htmlText] = await Promise.all([
        fetch(cssUrl).then(r=>r.text()),
        fetch(htmlUrl).then(r=>r.text())
      ]);
      const style = document.createElement('style');
      style.textContent = cssText;
      container.innerHTML = htmlText;
      root.appendChild(style);
      root.appendChild(container);
    }
  }

  customElements.define('site-header', SiteHeader);
  customElements.define('site-footer', SiteFooter);
})();// Adjust asset paths for pages under /views/
(function(){
  const underViews = location.pathname.indexOf('/views/') !== -1 || location.pathname.indexOf('\\views\\') !== -1;
  if(underViews){
    const h = document.querySelector('site-header');
    if(h && h.shadowRoot){ h.shadowRoot.querySelectorAll('img[src^="public/"]').forEach(img=>{ img.src = '../' + img.getAttribute('src'); }); }
    const f = document.querySelector('site-footer');
    if(f && f.shadowRoot){ f.shadowRoot.querySelectorAll('img[src^="public/"]').forEach(img=>{ img.src = '../' + img.getAttribute('src'); }); }
  }
})();
