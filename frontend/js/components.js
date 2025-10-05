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
      style.textContent = `${baseCss}\n/* responsive overrides */\n${responsiveCss}\n/* injected: CTA button when countdown ends */\n.header-cta-btn{display:inline-flex;align-items:center;gap:8px;padding:12px 18px;border-radius:10px;border:none;cursor:pointer;font-weight:800;background:linear-gradient(135deg,#e31e24 0%,#b71c1c 100%);color:#fff;box-shadow:0 8px 20px rgba(227,30,36,0.35),inset 0 -2px 6px rgba(0,0,0,0.06);text-decoration:none} .header-cta-btn:hover{transform:translateY(-2px) scale(1.02);box-shadow:0 10px 24px rgba(227,30,36,0.45);} .countdown-replaced{display:flex;justify-content:center;}`;
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
      let countdownTimerId = null;
      // Prefer global config; else try persisted localStorage; else ISO; else fallback
      let _cfg = null;
      if (window.ELECTION_DATE) {
        _cfg = window.ELECTION_DATE;
      } else {
        try {
          const raw = localStorage.getItem('ELECTION_DATE');
          if (raw) { _cfg = JSON.parse(raw); }
        } catch (_) { /* ignore */ }
      }
      if(_cfg){
        targetDate = computeBogotaUTC(_cfg);
      } else if(window.ELECTION_TARGET_ISO){
        try { targetDate = new Date(window.ELECTION_TARGET_ISO).getTime(); } catch(e){}
      }
      if(!targetDate){
        // Fallback por si no hay configuración global
        // Lunes 6 de octubre 2025, 6:00 am Bogotá (UTC-5)
        targetDate = new Date('2025-10-06T06:00:00-05:00').getTime();
      }
      function showVoteCTA(){
        const rootQuery = (sel)=> headerEl.querySelector(sel);
        const container = rootQuery('.contador') || headerEl; // fallback
        // Hide the time-left label when CTA is shown
        const titleEl = headerEl.querySelector('.titulo-evento');
        if (titleEl) { titleEl.style.display = 'none'; }
        const existingCountdown = rootQuery('.countdown');
        if(existingCountdown){ existingCountdown.classList.add('countdown-replaced'); existingCountdown.innerHTML = ''; }
        const link = document.createElement('a');
        const underViews = location.pathname.indexOf('/views/') !== -1 || location.pathname.indexOf('\\views\\') !== -1;
        link.href = underViews ? '/votaciones/' : '/votaciones/';
        link.className = 'header-cta-btn';
        link.textContent = 'Ir a votación';
        // insert
        if(existingCountdown){ existingCountdown.appendChild(link); }
        else { container.appendChild(link); }
        // Also enable the page-level CTA section if present
        try {
          const pageCTA = document.querySelector('.vote-cta');
          if (pageCTA) {
            pageCTA.classList.add('vote-cta--enabled', 'visible');
          }
          document.body.classList.add('countdown-ended');
        } catch(_){}
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
        if(d <= 0){
          if(countdownTimerId){ clearInterval(countdownTimerId); countdownTimerId = null; }
          showVoteCTA();
        }
      }
      updateCountdown();
      countdownTimerId = setInterval(updateCountdown, 1000);

      // Toggle collapse solo en móvil: en pantallas grandes no es clicable
      const countdownEl = headerEl.querySelector('.countdown');
      if (countdownEl) {
        const mq = window.matchMedia('(max-width: 768px)');
        let clickHandler = null;

        function enableInteractive(){
          if(clickHandler) return; // ya habilitado
          clickHandler = () => {
            const collapsed = countdownEl.classList.toggle('collapsed');
            countdownEl.setAttribute('aria-expanded', String(!collapsed));
          };
          countdownEl.style.cursor = 'pointer';
          countdownEl.setAttribute('role', 'button');
          countdownEl.setAttribute('aria-label', 'Mostrar/ocultar contador');
          countdownEl.setAttribute('aria-expanded', 'true');
          countdownEl.addEventListener('click', clickHandler);
        }

        function disableInteractive(){
          if(clickHandler){
            countdownEl.removeEventListener('click', clickHandler);
            clickHandler = null;
          }
          countdownEl.style.cursor = 'default';
          countdownEl.removeAttribute('role');
          countdownEl.removeAttribute('aria-label');
          countdownEl.removeAttribute('aria-expanded');
          countdownEl.classList.remove('collapsed');
        }

        function applyByViewport(e){
          if(e.matches){ enableInteractive(); } else { disableInteractive(); }
        }

        applyByViewport(mq);
        mq.addEventListener ? mq.addEventListener('change', applyByViewport) : mq.addListener(applyByViewport);
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
