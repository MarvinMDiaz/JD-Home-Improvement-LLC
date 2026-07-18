/**
 * JD Home Improvement: site chrome (mobile navigation)
 */
(function () {
  const nav = document.querySelector(".site-nav");
  const toggle = document.querySelector(".site-nav__toggle");
  const panel = document.getElementById("site-nav-menu");

  if (!nav || !toggle || !panel) return;

  const openLabel = "Open menu";
  const closeLabel = "Close menu";

  function setOpen(isOpen) {
    nav.classList.toggle("site-nav--open", isOpen);
    toggle.setAttribute("aria-expanded", String(isOpen));
    toggle.setAttribute("aria-label", isOpen ? closeLabel : openLabel);
  }

  toggle.addEventListener("click", function () {
    const next = !nav.classList.contains("site-nav--open");
    setOpen(next);
  });

  panel.querySelectorAll("a").forEach(function (link) {
    link.addEventListener("click", function () {
      setOpen(false);
    });
  });

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") setOpen(false);
  });

  document.addEventListener("click", function (e) {
    if (!nav.classList.contains("site-nav--open")) return;
    if (nav.contains(e.target)) return;
    setOpen(false);
  });

  window.addEventListener("resize", function () {
    if (window.matchMedia("(min-width: 781px)").matches) {
      setOpen(false);
    }
  });
})();

/**
 * Smooth scroll for in-page anchor links (nav, footer, skip link).
 * Uses scrollIntoView so behavior is consistent with browsers that only
 * partially apply CSS scroll-behavior; honors prefers-reduced-motion.
 */
(function () {
  var reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

  document.addEventListener(
    "click",
    function (e) {
      var a = e.target.closest("a[href]");
      if (!a) return;

      var hrefAttr = a.getAttribute("href");
      if (!hrefAttr || hrefAttr === "#") return;

      var url;
      try {
        url = new URL(a.href, window.location.href);
      } catch (err) {
        return;
      }

      if (url.origin !== window.location.origin || url.pathname !== window.location.pathname) {
        return;
      }

      var hash = url.hash;
      if (!hash || hash === "#") return;

      var id = decodeURIComponent(hash.slice(1));
      if (!id || !document.getElementById(id)) return;

      e.preventDefault();
      var el = document.getElementById(id);
      var behavior = reduceMotion.matches ? "auto" : "smooth";
      el.scrollIntoView({ behavior: behavior, block: "start" });
      if (history.pushState) {
        history.pushState(null, "", url.pathname + url.search + hash);
      }
    },
    false
  );
})();

/**
 * Projects: full-size image preview (lightbox)
 */
(function () {
  var root = document.querySelector(".projects-section");
  var dialog = document.getElementById("project-lightbox");
  if (!root || !dialog || typeof dialog.showModal !== "function") return;

  var largeImg = dialog.querySelector(".project-lightbox__img");
  if (!largeImg) return;

  root.querySelectorAll(".projects-card__shot").forEach(function (shot) {
    shot.setAttribute("tabindex", "0");
    shot.setAttribute("role", "button");
    var cap = shot.querySelector("figcaption.visually-hidden");
    var bit = cap && cap.textContent ? cap.textContent.trim() : "Photo";
    shot.setAttribute("aria-label", "Open preview: " + bit);
  });

  function openFromThumb(thumb) {
    var src = thumb.currentSrc || thumb.getAttribute("src") || "";
    if (!src) return;
    largeImg.src = src;
    largeImg.alt = thumb.getAttribute("alt") || "";
    dialog.showModal();
  }

  function closeLightbox() {
    if (!dialog.open || typeof dialog.close !== "function") return;
    dialog.close();
  }

  var closeBtn = dialog.querySelector(".project-lightbox__close");
  if (closeBtn) {
    closeBtn.addEventListener(
      "click",
      function (e) {
        e.preventDefault();
        window.setTimeout(function () {
          closeLightbox();
        }, 0);
      },
      false
    );
  }

  root.addEventListener(
    "click",
    function (e) {
      var shot = e.target.closest(".projects-card__shot");
      if (!shot || !root.contains(shot)) return;
      var thumb = shot.querySelector("img.projects-card__img");
      if (!thumb) return;
      openFromThumb(thumb);
    },
    false
  );

  root.addEventListener(
    "keydown",
    function (e) {
      if (e.key !== "Enter" && e.key !== " ") return;
      var shot = e.target.closest(".projects-card__shot");
      if (!shot || !root.contains(shot) || e.target !== shot) return;
      e.preventDefault();
      var thumb = shot.querySelector("img.projects-card__img");
      if (!thumb) return;
      openFromThumb(thumb);
    },
    false
  );

  dialog.addEventListener(
    "click",
    function (e) {
      if (e.target === dialog) closeLightbox();
    },
    false
  );

  dialog.addEventListener("close", function () {
    window.setTimeout(function () {
      largeImg.removeAttribute("src");
      largeImg.removeAttribute("srcset");
      largeImg.alt = "";
    }, 0);
  });
})();

/**
 * Projects section: category filter + multi-page gallery
 */
(function () {
  var root = document.querySelector(".projects-section");
  if (!root) return;

  var chips = root.querySelectorAll(".projects-filter__chip");
  var cards = root.querySelectorAll(".projects-card");
  var listEl = document.getElementById("projects-pagination-list");
  var btnPrev = document.getElementById("projects-pagination-prev");
  var btnNext = document.getElementById("projects-pagination-next");
  var live = document.getElementById("projects-pagination-live");
  var meta = document.getElementById("projects-pagination-meta");

  if (!chips.length || !cards.length) return;

  var pageHosts = Array.from(root.querySelectorAll(".projects-section__page")).filter(function (el) {
    return el.querySelector(".projects-card");
  });
  if (!pageHosts.length || !listEl) return;

  var currentPage = 1;

  function applyFilter(filter) {
    cards.forEach(function (card) {
      var cats = (card.getAttribute("data-categories") || "").trim().split(/\s+/);
      var show = filter === "all" || cats.indexOf(filter) !== -1;
      card.toggleAttribute("hidden", !show);
    });
  }

  function firstPageWithVisibleCards() {
    for (var i = 0; i < pageHosts.length; i++) {
      var any = false;
      pageHosts[i].querySelectorAll(".projects-card").forEach(function (card) {
        if (!card.hasAttribute("hidden")) any = true;
      });
      if (any) return i + 1;
    }
    return 1;
  }

  function updatePaginationUI() {
    var max = pageHosts.length;
    if (btnPrev) btnPrev.disabled = currentPage <= 1;
    if (btnNext) btnNext.disabled = currentPage >= max;

    listEl.innerHTML = "";
    for (var p = 1; p <= max; p++) {
      var li = document.createElement("li");
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "projects-pagination__num" + (p === currentPage ? " projects-pagination__num--active" : "");
      btn.textContent = String(p);
      btn.setAttribute("aria-label", "Page " + p);
      if (p === currentPage) btn.setAttribute("aria-current", "page");
      (function (pageNum) {
        btn.addEventListener("click", function () {
          goToPage(pageNum);
        });
      })(p);
      li.appendChild(btn);
      listEl.appendChild(li);
    }

    var msg = "Page " + currentPage + " of " + max;
    if (live) live.textContent = msg;
    if (meta) meta.textContent = msg;
  }

  function goToPage(n) {
    var max = pageHosts.length;
    currentPage = Math.max(1, Math.min(n, max));
    pageHosts.forEach(function (page, i) {
      page.hidden = i !== currentPage - 1;
    });
    updatePaginationUI();
  }

  chips.forEach(function (chip) {
    chip.addEventListener("click", function () {
      var filter = chip.getAttribute("data-filter") || "all";
      chips.forEach(function (c) {
        var on = c === chip;
        c.classList.toggle("projects-filter__chip--active", on);
        c.setAttribute("aria-pressed", on ? "true" : "false");
      });
      applyFilter(filter);
      goToPage(firstPageWithVisibleCards());
    });
  });

  if (btnPrev) {
    btnPrev.addEventListener("click", function () {
      goToPage(currentPage - 1);
    });
  }
  if (btnNext) {
    btnNext.addEventListener("click", function () {
      goToPage(currentPage + 1);
    });
  }

  applyFilter("all");
  goToPage(1);
})();

/**
 * Single-page nav: highlight section link while scrolling
 */
(function () {
  var sectionIds = [
    "hero",
    "about",
    "services",
    "projects",
    "faq",
    "contact",
  ];
  var links = document.querySelectorAll(".site-nav__link[data-nav-section]");
  if (!links.length) return;

  function navOffset() {
    var h = document.querySelector(".site-header");
    return h ? h.getBoundingClientRect().height + 12 : 96;
  }

  function currentSection() {
    var offset = navOffset();
    var y = window.scrollY + offset;
    var best = "hero";
    for (var i = 0; i < sectionIds.length; i++) {
      var id = sectionIds[i];
      var el = document.getElementById(id);
      if (!el) continue;
      var top = window.scrollY + el.getBoundingClientRect().top;
      if (top <= y + 1) best = id;
    }
    return best;
  }

  function setActive(id) {
    links.forEach(function (link) {
      var on = link.getAttribute("data-nav-section") === id;
      link.classList.toggle("site-nav__link--active", on);
      if (on) link.setAttribute("aria-current", "page");
      else link.removeAttribute("aria-current");
    });
  }

  var ticking = false;
  function onScrollOrResize() {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(function () {
      ticking = false;
      setActive(currentSection());
    });
  }

  window.addEventListener("scroll", onScrollOrResize, { passive: true });
  window.addEventListener("resize", onScrollOrResize);
  window.addEventListener("hashchange", onScrollOrResize);
  window.addEventListener("load", onScrollOrResize);
  onScrollOrResize();
})();

/**
 * Contact form: AJAX submit (Amazon SES handled server-side)
 */
(function () {
  var form = document.getElementById("contact-form");
  if (!form) return;

  var successPanel = document.getElementById("contact-form-success");
  var footnote = document.getElementById("contact-footnote");
  var submitBtn = document.getElementById("contact-submit");
  var globalErr = document.getElementById("contact-form-global-error");
  var meta = document.querySelector('meta[name="csrf-token"]');
  var token = meta ? meta.getAttribute("content") : "";

  var feedback = document.getElementById("contact-feedback");
  if (feedback && window.location.search.indexOf("sent=1") !== -1) {
    if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      feedback.scrollIntoView({ behavior: "smooth", block: "center" });
    } else {
      feedback.scrollIntoView({ block: "center" });
    }
  }

  var confettiCanvas = document.getElementById("contact-confetti");
  var revertTimer = null;
  var confettiStopFn = null;

  function launchConfetti() {
    if (!confettiCanvas) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    var ctx = confettiCanvas.getContext("2d");
    if (!ctx) return;

    var card = confettiCanvas.parentElement;
    var rect = card.getBoundingClientRect();
    var dpr = window.devicePixelRatio || 1;
    confettiCanvas.width = rect.width * dpr;
    confettiCanvas.height = rect.height * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    var colors = ["#f5c542", "#ffd54f", "#e6aa1a", "#1a1814", "#faf9f7"];
    var count = Math.max(50, Math.min(110, Math.round((rect.width * rect.height) / 1400)));
    // Each piece falls the full card height (plus a little overshoot both ends)
    // over its own randomized duration, scaled to the card's actual size so the
    // effect looks right whether the card is a short desktop row or a tall
    // stacked mobile column.
    var fallDistance = rect.height + 70;
    var maxDuration = 0;
    var particles = [];
    for (var i = 0; i < count; i++) {
      var duration = 1700 + Math.random() * 1300;
      maxDuration = Math.max(maxDuration, duration);
      particles.push({
        startX: Math.random() * rect.width,
        startY: -30 - Math.random() * 40,
        swayAmp: 10 + Math.random() * 18,
        swayFreq: 1.2 + Math.random() * 1.6,
        swayPhase: Math.random() * Math.PI * 2,
        delay: Math.random() * 350,
        duration: duration,
        size: Math.random() * 5 + 4,
        color: colors[Math.floor(Math.random() * colors.length)],
        rotationSpeed: (Math.random() - 0.5) * 6,
        shape: Math.random() > 0.5 ? "rect" : "circle",
      });
    }

    var startTime = null;
    var totalDuration = maxDuration + 350;
    var rafId = null;

    function frame(ts) {
      if (!startTime) startTime = ts;
      var elapsed = ts - startTime;

      ctx.clearRect(0, 0, rect.width, rect.height);

      particles.forEach(function (p) {
        var t = elapsed - p.delay;
        if (t < 0) return;
        var progress = Math.min(1, t / p.duration);
        // Ease-in fall: starts slow, accelerates like gravity would.
        var eased = progress * progress;
        var y = p.startY + fallDistance * eased;
        var x = p.startX + Math.sin(progress * Math.PI * p.swayFreq + p.swayPhase) * p.swayAmp;
        var rotation = t * 0.01 * p.rotationSpeed;
        var life = progress > 0.8 ? Math.max(0, 1 - (progress - 0.8) / 0.2) : 1;

        ctx.save();
        ctx.globalAlpha = life;
        ctx.translate(x, y);
        ctx.rotate(rotation);
        ctx.fillStyle = p.color;
        if (p.shape === "rect") {
          ctx.fillRect(-p.size / 2, -p.size / 4, p.size, p.size / 2);
        } else {
          ctx.beginPath();
          ctx.arc(0, 0, p.size / 2.4, 0, Math.PI * 2);
          ctx.fill();
        }
        ctx.restore();
      });

      if (elapsed < totalDuration) {
        rafId = window.requestAnimationFrame(frame);
      } else {
        ctx.clearRect(0, 0, rect.width, rect.height);
      }
    }

    rafId = window.requestAnimationFrame(frame);

    confettiStopFn = function () {
      if (rafId) window.cancelAnimationFrame(rafId);
      ctx.clearRect(0, 0, rect.width, rect.height);
    };
  }

  function showSuccess() {
    form.hidden = true;
    if (footnote) footnote.hidden = true;
    if (successPanel) successPanel.hidden = false;

    launchConfetti();

    if (revertTimer) window.clearTimeout(revertTimer);
    revertTimer = window.setTimeout(function () {
      if (confettiStopFn) confettiStopFn();
      if (successPanel) successPanel.hidden = true;
      form.hidden = false;
      if (footnote) footnote.hidden = false;
      form.reset();
      clearErrors();
    }, 5000);
  }

  function clearErrors() {
    if (globalErr) {
      globalErr.hidden = true;
      globalErr.textContent = "";
    }
    form.querySelectorAll(".contact-field__error").forEach(function (el) {
      el.hidden = true;
      el.textContent = "";
    });
    form.querySelectorAll(".contact-field__input").forEach(function (input) {
      input.classList.remove("contact-field__input--error");
      input.removeAttribute("aria-invalid");
    });
  }

  function showFieldErrors(errors) {
    Object.keys(errors).forEach(function (field) {
      var msg = errors[field];
      var input = form.querySelector('[name="' + field + '"]');
      var errEl = document.getElementById("contact-" + field + "-error");
      if (input && errEl) {
        errEl.textContent = msg;
        errEl.hidden = false;
        input.classList.add("contact-field__input--error");
        input.setAttribute("aria-invalid", "true");
      }
    });
  }

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    if (!form.checkValidity()) {
      form.reportValidity();
      return;
    }
    clearErrors();

    var fd = new FormData(form);
    var payload = {
      name: fd.get("name"),
      email: fd.get("email"),
      phone: fd.get("phone"),
      topic: fd.get("topic"),
      message: fd.get("message"),
      company_website_confirm: fd.get("company_website_confirm"),
    };

    form.classList.add("is-loading");
    submitBtn.disabled = true;

    fetch(form.action, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        "X-CSRFToken": token,
        "X-Requested-With": "XMLHttpRequest",
      },
      body: JSON.stringify(payload),
    })
      .then(function (r) {
        return r.json().then(function (data) {
          return { ok: r.ok, status: r.status, data: data };
        });
      })
      .then(function (res) {
        if (res.ok && res.data && res.data.ok) {
          showSuccess();
          return;
        }
        if (res.data && res.data.errors) {
          showFieldErrors(res.data.errors);
          return;
        }
        if (res.data && res.data.error === "csrf") {
          if (globalErr) {
            globalErr.textContent =
              "Your session expired. Please refresh the page and try again.";
            globalErr.hidden = false;
          }
          return;
        }
        var msg =
          res.data && res.data.message
            ? res.data.message
            : "Something went wrong. Please try again.";
        if (globalErr) {
          globalErr.textContent = msg;
          globalErr.hidden = false;
        }
      })
      .catch(function () {
        if (globalErr) {
          globalErr.textContent =
            "We couldn’t send your message. Check your connection and try again, or email us directly.";
          globalErr.hidden = false;
        }
      })
      .finally(function () {
        form.classList.remove("is-loading");
        submitBtn.disabled = false;
      });
  });
})();

(function () {
  var el = document.getElementById("footer-year");
  if (el) el.textContent = String(new Date().getFullYear());
})();
