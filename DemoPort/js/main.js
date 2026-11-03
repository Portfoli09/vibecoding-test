(function () {
  "use strict";

  var CATEGORY_LABEL = { python: "Python", web: "Web", ios: "iOS" };
  var LINK_LABEL = { github: "GitHub", demo: "라이브 데모", appstore: "App Store" };

  // ----- 모바일 메뉴 -----
  var toggle = document.querySelector(".nav__toggle");
  var menu = document.getElementById("nav-menu");

  function setMenu(open) {
    toggle.setAttribute("aria-expanded", String(open));
    toggle.setAttribute("aria-label", open ? "메뉴 닫기" : "메뉴 열기");
    menu.classList.toggle("is-open", open);
  }

  toggle.addEventListener("click", function () {
    setMenu(toggle.getAttribute("aria-expanded") !== "true");
  });

  menu.addEventListener("click", function (e) {
    if (e.target.closest("a")) setMenu(false);
  });

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && menu.classList.contains("is-open")) {
      setMenu(false);
      toggle.focus();
    }
  });

  // ----- 프로젝트 카드 렌더링 -----
  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text) node.textContent = text;
    return node;
  }

  function renderProjects(projects) {
    var list = document.getElementById("project-list");
    if (!list) return;

    projects.forEach(function (p) {
      var card = el("article", "project-card reveal");

      var thumb = el("div", "project-card__thumb project-card__thumb--" + p.category, CATEGORY_LABEL[p.category] || "");
      thumb.setAttribute("aria-hidden", "true");
      card.appendChild(thumb);

      var body = el("div", "project-card__body");
      body.appendChild(el("h3", "project-card__title", p.title));
      body.appendChild(el("p", "project-card__desc", p.description));

      var tags = el("ul", "tags");
      tags.setAttribute("aria-label", "사용 기술");
      (p.tags || []).forEach(function (t) {
        tags.appendChild(el("li", null, t));
      });
      body.appendChild(tags);

      var links = el("div", "project-card__links");
      Object.keys(p.links || {}).forEach(function (key) {
        var url = p.links[key];
        if (!url) return;
        var a = el("a", null, LINK_LABEL[key] || key);
        a.href = url;
        a.target = "_blank";
        a.rel = "noopener";
        links.appendChild(a);
      });
      if (links.children.length) body.appendChild(links);

      card.appendChild(body);
      list.appendChild(card);
    });
  }

  renderProjects(window.PROJECTS || []);

  // ----- 이메일 (스팸 수집 방지를 위해 런타임에 조합) -----
  var emailLink = document.getElementById("email-link");
  var emailButton = document.getElementById("email-button");
  if (emailLink) {
    var address = emailLink.dataset.user + "@" + emailLink.dataset.domain;
    emailLink.textContent = address;
    emailLink.href = "mailto:" + address;
    if (emailButton) emailButton.href = "mailto:" + address;
  }

  // ----- 푸터 연도 -----
  var year = document.getElementById("year");
  if (year) year.textContent = new Date().getFullYear();

  // ----- 스크롤 등장 애니메이션 -----
  document.querySelectorAll(".section__title, .skill-card, .about").forEach(function (node) {
    node.classList.add("reveal");
  });

  var targets = document.querySelectorAll(".reveal");
  if ("IntersectionObserver" in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12 });
    targets.forEach(function (t) { io.observe(t); });
  } else {
    targets.forEach(function (t) { t.classList.add("is-visible"); });
  }
})();
