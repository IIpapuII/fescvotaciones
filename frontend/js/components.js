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
      const responsiveCssUrl = resolveFromScript('../css/css-responsive.css');
      const htmlUrl = resolveFromScript((location.pathname.indexOf('/views/') !== -1 || location.pathname.indexOf('\\\\views\\\\') !== -1) ? '../components/header.views.html' : '../components/header.html');
      const [baseCss, responsiveCss, htmlText] = await Promise.all([
        fetch(cssUrl).then(r=>r.text()),
        fetch(responsiveCssUrl).then(r=>r.text()).catch(()=>''),
        fetch(htmlUrl).then(r=>r.text())
      ]);
      const style = document.createElement('style');
      style.textContent = `${baseCss}\n/* responsive overrides */\n${responsiveCss}`;
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

      // Countdown logic (reads global config if available)
      function computeBogotaUTC(dateObj){
        if(!dateObj) return null;
        var y = dateObj.year, m = dateObj.month, d = dateObj.day, hh = dateObj.hour || 0, mm = dateObj.minute || 0;
        return Date.UTC(y, (m||1)-1, d, (hh||0)+5, mm||0, 0);
      }
      let targetDate = null;
      if(window.ELECTION_DATE){
        targetDate = computeBogotaUTC(window.ELECTION_DATE);
      } else if(window.ELECTION_TARGET_ISO){
        try { targetDate = new Date(window.ELECTION_TARGET_ISO).getTime(); } catch(e){}
      }
      if(!targetDate){
        // Fallback por si no hay configuración global
        // Lunes 6 de octubre 2025, 6:00 am Bogotá (UTC-5)
        targetDate = new Date('2025-10-06T06:00:00-05:00').getTime();
      }
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

      // Toggle collapse on mobile: make countdown act like a FAB button
      const countdownEl = headerEl.querySelector('.countdown');
      if (countdownEl) {
        countdownEl.style.cursor = 'pointer';
        countdownEl.setAttribute('role', 'button');
        countdownEl.setAttribute('aria-label', 'Mostrar/ocultar contador');
        countdownEl.setAttribute('aria-expanded', 'true');
        countdownEl.addEventListener('click', () => {
          const collapsed = countdownEl.classList.toggle('collapsed');
          countdownEl.setAttribute('aria-expanded', String(!collapsed));
        });
      }
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
