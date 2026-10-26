(function () {
    const menuWraps = Array.from(document.querySelectorAll("[data-menu]"));
    const mobileToggle = document.querySelector("[data-mobile-toggle]");
    const mobileMenu = document.querySelector("[data-mobile-menu]");
    const themeToggle = document.querySelector("[data-theme-toggle]");
    const themeKey = "dramaboard-theme";

    function isDarkTheme() {
        return document.documentElement.getAttribute("data-theme") === "dark";
    }

    function syncThemeToggle() {
        if (!themeToggle) {
            return;
        }

        themeToggle.setAttribute("aria-pressed", String(isDarkTheme()));
    }

    if (themeToggle) {
        syncThemeToggle();

        themeToggle.addEventListener("click", function () {
            const nextTheme = isDarkTheme() ? "light" : "dark";

            if (nextTheme === "dark") {
                document.documentElement.setAttribute("data-theme", "dark");
            } else {
                document.documentElement.removeAttribute("data-theme");
            }

            try {
                localStorage.setItem(themeKey, nextTheme);
            } catch (error) {}

            syncThemeToggle();
        });
    }

    function setMenuState(wrap, isOpen) {
        const trigger = wrap.querySelector("[data-menu-trigger]");
        const panel = wrap.querySelector("[data-menu-panel]");

        wrap.classList.toggle("is-open", isOpen);

        if (trigger) {
            trigger.setAttribute("aria-expanded", String(isOpen));
        }

        if (panel) {
            panel.setAttribute("aria-hidden", String(!isOpen));
        }
    }

    function closeMenus(except) {
        menuWraps.forEach(function (wrap) {
            if (wrap !== except) {
                setMenuState(wrap, false);
            }
        });
    }

    menuWraps.forEach(function (wrap) {
        const trigger = wrap.querySelector("[data-menu-trigger]");
        const panel = wrap.querySelector("[data-menu-panel]");

        if (!trigger || !panel) {
            return;
        }

        trigger.addEventListener("click", function (event) {
            event.stopPropagation();
            const willOpen = !wrap.classList.contains("is-open");

            closeMenus(wrap);
            setMenuState(wrap, willOpen);
        });

        panel.addEventListener("click", function (event) {
            event.stopPropagation();
        });
    });

    function setMobileMenu(isOpen) {
        if (!mobileToggle || !mobileMenu) {
            return;
        }

        mobileMenu.classList.toggle("is-open", isOpen);
        mobileToggle.classList.toggle("is-active", isOpen);
        mobileToggle.setAttribute("aria-expanded", String(isOpen));
        mobileToggle.setAttribute("aria-label", isOpen ? "Close navigation" : "Open navigation");
    }

    if (mobileToggle && mobileMenu) {
        mobileToggle.addEventListener("click", function (event) {
            event.stopPropagation();
            setMobileMenu(!mobileMenu.classList.contains("is-open"));
        });

        mobileMenu.addEventListener("click", function (event) {
            event.stopPropagation();
        });

        mobileMenu.querySelectorAll("a").forEach(function (link) {
            link.addEventListener("click", function () {
                setMobileMenu(false);
            });
        });
    }

    document.addEventListener("click", function () {
        closeMenus();
        setMobileMenu(false);
    });

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape") {
            const openTrigger = document.querySelector("[data-menu].is-open [data-menu-trigger]");
            const mobileWasOpen = mobileMenu && mobileMenu.classList.contains("is-open");

            closeMenus();
            setMobileMenu(false);

            if (openTrigger) {
                openTrigger.focus();
            } else if (mobileWasOpen && mobileToggle) {
                mobileToggle.focus();
            }
        }
    });
})();

(function () {
    const carousel = document.querySelector("[data-hero-carousel]");

    if (!carousel) {
        return;
    }

    const track = carousel.querySelector("[data-hero-track]");
    const slides = Array.prototype.slice.call(carousel.querySelectorAll("[data-hero-slide]"));
    const previous = carousel.querySelector("[data-hero-prev]");
    const next = carousel.querySelector("[data-hero-next]");
    const dots = Array.prototype.slice.call(carousel.querySelectorAll("[data-hero-dot]"));
    const status = carousel.querySelector("[data-hero-status]");
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
    const canHover = window.matchMedia("(hover: hover)");
    const autoplayDelay = 6000;
    let activeIndex = 0;
    let scrollFrame = null;
    let autoplayTimer = null;
    let autoplayPaused = false;

    if (!track || slides.length === 0) {
        return;
    }

    carousel.querySelectorAll("[data-hero-poster]").forEach(function (image) {
        function hideImage() {
            image.hidden = true;
        }

        image.addEventListener("error", hideImage);

        if (image.complete && image.naturalWidth === 0) {
            hideImage();
        }
    });

    function slideOffset(slide) {
        return slide.getBoundingClientRect().left - track.getBoundingClientRect().left + track.scrollLeft;
    }

    function nearestIndex() {
        const trackLeft = track.getBoundingClientRect().left;
        let nearest = 0;
        let shortest = Infinity;

        slides.forEach(function (slide, index) {
            const distance = Math.abs(slide.getBoundingClientRect().left - trackLeft);

            if (distance < shortest) {
                shortest = distance;
                nearest = index;
            }
        });

        return nearest;
    }

    function sync(index, announce) {
        activeIndex = Math.max(0, Math.min(slides.length - 1, index));

        dots.forEach(function (dot, dotIndex) {
            const isActive = dotIndex === activeIndex;

            dot.classList.toggle("is-active", isActive);

            if (isActive) {
                dot.setAttribute("aria-current", "true");
            } else {
                dot.removeAttribute("aria-current");
            }
        });

        if (previous) {
            previous.disabled = activeIndex === 0;
        }

        if (next) {
            next.disabled = activeIndex === slides.length - 1;
        }

        if (announce && status) {
            const title = slides[activeIndex].querySelector(".hero-title");
            const label = title ? title.textContent.trim() : "";

            status.textContent = "Slide " + (activeIndex + 1) + " of " + slides.length + (label ? ": " + label : "");
        }
    }

    function goTo(index, announce) {
        const target = Math.max(0, Math.min(slides.length - 1, index));

        sync(target, announce);
        track.scrollTo({
            left: slideOffset(slides[target]),
            behavior: reduceMotion.matches ? "auto" : "smooth"
        });
    }

    function stopAutoplay() {
        if (autoplayTimer) {
            window.clearInterval(autoplayTimer);
            autoplayTimer = null;
        }
    }

    function startAutoplay() {
        stopAutoplay();

        if (slides.length < 2 || reduceMotion.matches || autoplayPaused || document.hidden) {
            return;
        }

        autoplayTimer = window.setInterval(function () {
            goTo((activeIndex + 1) % slides.length, false);
        }, autoplayDelay);
    }

    function pauseAutoplay() {
        autoplayPaused = true;
        stopAutoplay();
    }

    function resumeAutoplay() {
        autoplayPaused = false;
        startAutoplay();
    }

    if (previous) {
        previous.addEventListener("click", function () {
            goTo(activeIndex - 1, true);
        });
    }

    if (next) {
        next.addEventListener("click", function () {
            goTo(activeIndex + 1, true);
        });
    }

    dots.forEach(function (dot) {
        dot.addEventListener("click", function () {
            goTo(Number(dot.getAttribute("data-hero-dot")), true);
        });
    });

    track.addEventListener("scroll", function () {
        if (scrollFrame) {
            window.cancelAnimationFrame(scrollFrame);
        }

        scrollFrame = window.requestAnimationFrame(function () {
            const nearest = nearestIndex();

            if (nearest !== activeIndex) {
                sync(nearest, false);
            }
        });
    }, { passive: true });

    track.addEventListener("keydown", function (event) {
        if (event.target !== track) {
            return;
        }

        if (event.key === "ArrowLeft") {
            event.preventDefault();
            goTo(activeIndex - 1, true);
        } else if (event.key === "ArrowRight") {
            event.preventDefault();
            goTo(activeIndex + 1, true);
        }
    });

    if (canHover.matches) {
        carousel.addEventListener("pointerenter", pauseAutoplay);
        carousel.addEventListener("pointerleave", resumeAutoplay);
    }

    carousel.addEventListener("focusin", pauseAutoplay);
    carousel.addEventListener("focusout", function (event) {
        if (!carousel.contains(event.relatedTarget)) {
            resumeAutoplay();
        }
    });

    document.addEventListener("visibilitychange", function () {
        if (document.hidden) {
            stopAutoplay();
        } else {
            startAutoplay();
        }
    });

    if (reduceMotion.addEventListener) {
        reduceMotion.addEventListener("change", function () {
            if (reduceMotion.matches) {
                stopAutoplay();
            } else {
                startAutoplay();
            }
        });
    }

    window.addEventListener("resize", function () {
        track.scrollTo({ left: slideOffset(slides[activeIndex]), behavior: "auto" });
    });

    sync(0, false);
    startAutoplay();
})();
