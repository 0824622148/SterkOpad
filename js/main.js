/**
 * STERK OPAD ENTERTAINMENT — main.js
 * Vanilla JS only. No frameworks.
 *
 * Sections:
 * 1. Nav: scroll behaviour + mobile hamburger
 * 2. Scroll animations (IntersectionObserver)
 * 3. Floating CTA visibility
 * 4. Lightbox
 * 5. Form handling
 * 6. Contact page tabs
 * 7. Active nav link
 */

(function () {
  'use strict';

  /* ============================================================
     1. NAVIGATION
     ============================================================ */
  const nav = document.querySelector('.nav');
  const hamburger = document.querySelector('.nav__hamburger');
  const mobileNav = document.querySelector('.nav__mobile');
  const mobileLinks = document.querySelectorAll('.nav__mobile a');

  // Sticky nav on scroll
  function handleNavScroll() {
    if (window.scrollY > 60) {
      nav && nav.classList.add('scrolled');
    } else {
      nav && nav.classList.remove('scrolled');
    }
  }

  window.addEventListener('scroll', handleNavScroll, { passive: true });
  handleNavScroll(); // run on load

  // Mobile hamburger toggle
  function toggleMobileNav() {
    if (!hamburger || !mobileNav) return;
    const isOpen = hamburger.classList.toggle('open');
    mobileNav.classList.toggle('open', isOpen);
    document.body.style.overflow = isOpen ? 'hidden' : '';
  }

  function closeMobileNav() {
    if (!hamburger || !mobileNav) return;
    hamburger.classList.remove('open');
    mobileNav.classList.remove('open');
    document.body.style.overflow = '';
  }

  hamburger && hamburger.addEventListener('click', toggleMobileNav);
  mobileLinks.forEach(link => link.addEventListener('click', closeMobileNav));

  // Close mobile nav on Escape key
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closeMobileNav();
  });

  /* ============================================================
     2. SCROLL ANIMATIONS (IntersectionObserver)
     ============================================================ */
  const animatedEls = document.querySelectorAll('.animate-in');

  if (animatedEls.length > 0 && 'IntersectionObserver' in window) {
    const observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add('visible');
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.12, rootMargin: '0px 0px -40px 0px' }
    );

    animatedEls.forEach(function (el) {
      observer.observe(el);
    });
  } else {
    // Fallback: show all immediately
    animatedEls.forEach(function (el) {
      el.classList.add('visible');
    });
  }

  /* ============================================================
     3. FLOATING CTA VISIBILITY
     ============================================================ */
  const floatCta = document.querySelector('.float-cta');

  if (floatCta) {
    function handleFloatCta() {
      if (window.scrollY > 300) {
        floatCta.classList.add('visible');
      } else {
        floatCta.classList.remove('visible');
      }
    }
    window.addEventListener('scroll', handleFloatCta, { passive: true });
    handleFloatCta();
  }

  /* ============================================================
     4. LIGHTBOX
     ============================================================ */
  const lightbox = document.getElementById('lightbox');

  if (lightbox) {
    const lightboxImg = lightbox.querySelector('.lightbox__img');
    const closeBtn = lightbox.querySelector('.lightbox__close');
    const prevBtn = lightbox.querySelector('.lightbox__prev');
    const nextBtn = lightbox.querySelector('.lightbox__next');
    const galleryItems = Array.from(document.querySelectorAll('.gallery-item[data-src]'));

    let currentIndex = 0;

    function openLightbox(index) {
      currentIndex = index;
      lightboxImg.src = galleryItems[index].dataset.src;
      lightboxImg.alt = galleryItems[index].dataset.alt || '';
      lightbox.classList.add('open');
      document.body.style.overflow = 'hidden';
    }

    function closeLightbox() {
      lightbox.classList.remove('open');
      document.body.style.overflow = '';
      lightboxImg.src = '';
    }

    function showPrev() {
      currentIndex = (currentIndex - 1 + galleryItems.length) % galleryItems.length;
      lightboxImg.src = galleryItems[currentIndex].dataset.src;
    }

    function showNext() {
      currentIndex = (currentIndex + 1) % galleryItems.length;
      lightboxImg.src = galleryItems[currentIndex].dataset.src;
    }

    galleryItems.forEach(function (item, index) {
      item.addEventListener('click', function () { openLightbox(index); });
    });

    closeBtn && closeBtn.addEventListener('click', closeLightbox);
    prevBtn && prevBtn.addEventListener('click', showPrev);
    nextBtn && nextBtn.addEventListener('click', showNext);

    // Click outside image to close
    lightbox.addEventListener('click', function (e) {
      if (e.target === lightbox) closeLightbox();
    });

    // Keyboard navigation
    document.addEventListener('keydown', function (e) {
      if (!lightbox.classList.contains('open')) return;
      if (e.key === 'Escape') closeLightbox();
      if (e.key === 'ArrowLeft') showPrev();
      if (e.key === 'ArrowRight') showNext();
    });
  }

  /* ============================================================
     5. FORM HANDLING
     ============================================================ */
  const forms = document.querySelectorAll('.contact-form');

  forms.forEach(function (form) {
    form.addEventListener('submit', function (e) {
      const successEl = form.querySelector('.form-success');
      const submitBtn = form.querySelector('[type="submit"]');

      // Validate all required fields
      const required = form.querySelectorAll('[required]');
      let allFilled = true;

      required.forEach(function (field) {
        if (!field.value.trim()) {
          allFilled = false;
          field.style.borderColor = 'var(--red)';
          field.addEventListener('input', function () {
            field.style.borderColor = '';
          }, { once: true });
        }
      });

      if (!allFilled) {
        e.preventDefault();
        return;
      }

      // If using mailto (default), let browser handle it.
      // If using Formspree or similar, intercept here:
      /*
      e.preventDefault();
      submitBtn && (submitBtn.textContent = 'Sending...');
      submitBtn && (submitBtn.disabled = true);

      fetch(form.action, {
        method: 'POST',
        body: new FormData(form),
        headers: { 'Accept': 'application/json' }
      }).then(function (res) {
        if (res.ok) {
          form.reset();
          successEl && successEl.classList.add('visible');
        }
      }).finally(function () {
        submitBtn && (submitBtn.textContent = 'Send Message');
        submitBtn && (submitBtn.disabled = false);
      });
      */
    });
  });

  /* ============================================================
     6. CONTACT PAGE TABS
     ============================================================ */
  const contactTabs = document.querySelectorAll('.contact-tab');
  const formSections = document.querySelectorAll('.form-section[data-tab]');

  if (contactTabs.length > 0) {
    function switchTab(tabName) {
      contactTabs.forEach(function (tab) {
        tab.classList.toggle('active', tab.dataset.tab === tabName);
      });
      formSections.forEach(function (section) {
        section.style.display = section.dataset.tab === tabName ? 'block' : 'none';
      });
    }

    contactTabs.forEach(function (tab) {
      tab.addEventListener('click', function () {
        switchTab(tab.dataset.tab);
        // Update URL hash without scrolling
        history.replaceState(null, '', '#' + tab.dataset.tab);
      });
    });

    // On load, check hash to set initial tab
    const hash = window.location.hash.replace('#', '');
    const validTabs = Array.from(contactTabs).map(t => t.dataset.tab);
    if (hash && validTabs.includes(hash)) {
      switchTab(hash);
    } else if (contactTabs[0]) {
      switchTab(contactTabs[0].dataset.tab);
    }
  }

  /* ============================================================
     7. ACTIVE NAV LINK
     ============================================================ */
  const currentPath = window.location.pathname.split('/').pop() || 'index.html';
  const navLinks = document.querySelectorAll('.nav__links a, .nav__mobile a');

  navLinks.forEach(function (link) {
    const href = link.getAttribute('href');
    if (
      href === currentPath ||
      (currentPath === '' && href === 'index.html') ||
      (currentPath === 'index.html' && href === 'index.html')
    ) {
      link.classList.add('active');
    }
  });

  /* ============================================================
     8. SMOOTH SCROLL FOR ANCHOR LINKS
     ============================================================ */
  document.querySelectorAll('a[href^="#"]').forEach(function (anchor) {
    anchor.addEventListener('click', function (e) {
      const target = document.querySelector(this.getAttribute('href'));
      if (target) {
        e.preventDefault();
        const navHeight = parseInt(getComputedStyle(document.documentElement).getPropertyValue('--nav-height')) || 72;
        const top = target.getBoundingClientRect().top + window.scrollY - navHeight;
        window.scrollTo({ top: top, behavior: 'smooth' });
      }
    });
  });

})();
