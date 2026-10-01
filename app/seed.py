from datetime import datetime, timedelta, timezone

_P = [
("Welcome to the UASE Tech Studio blog", "Who we are, what we build, and what you'll find here.", ["uase", "studio"],
"""UASE Tech Studio Ltd is a software engineering studio in Abuja, Nigeria. We build **websites, web apps and iOS & Android apps** for businesses and institutions, from the first conversation to the App Store.

This blog is where we share:

- **Our stack and our work**: what we build with and why.
- **Lessons from shipping**: real problems and how we solved them.
- **Tech in general and Nigeria in particular**: what building and learning tech here is actually like.

Comments are open to everyone. Leave a name, or stay a ghost. If a post helped you, hit the like button."""),
("Why we build on Next.js, FastAPI and Capacitor", "Our main stack, and the reasoning behind it.", ["stack", "nextjs", "fastapi"],
"""Our current focus stack is **Next.js + TypeScript** on the front end, **FastAPI (Python)** on the back end, **MongoDB Atlas** for data, and **Capacitor** to turn the web app into native iOS and Android apps.

Why this combination?

1. **One codebase, three platforms.** The same interface serves the browser, the App Store and Google Play.
2. **Fast, typed APIs.** FastAPI gives quick development, automatic validation and clean documentation.
3. **Economical and minimal.** Vercel for the front end and Render for the API keep running costs low and scaling simple.

We still work with Django, PHP and MySQL when a project calls for them. The stack serves the problem, not the other way round."""),
("From client problem to App Store: how we deliver", "Our end-to-end process in ten steps.", ["process", "delivery"],
"""Every product we ship follows the same path:

1. **Planning**: turn the problem into scope, roles and priorities.
2. **Architecture**: choose the structure, data model and access rules.
3. **Design**: consistent UI and UX for web and mobile.
4. **Technology choices**: safe, robust, scalable and economical.
5. **Building**: write and compile the frontend, backend and native shells.
6. **Debugging**: fix errors across web, iOS and Android builds.
7. **Testing**: every role and flow, on real devices.
8. **Launch**: web first, then Google Play and the App Store.
9. **Team walkthrough**: present and test with the client's team.
10. **Continuous upgrades**: keep adding features that solve modern problems and make the app easier to use.

The evidence of a process that works is a product people can download."""),
("Lessons from shipping a web app to iOS and Android", "Practical things that bit us, so they don't bite you.", ["mobile", "capacitor", "lessons"],
"""Wrapping a web app in Capacitor is fast, but the last 10% takes care:

- **Safe areas.** Notches and status bars can double your padding. Handle them once, in global CSS, not per component.
- **Push notifications.** Google retired the legacy Firebase server key. Use **FCM V1** with a service account from the start.
- **Permission strings.** iOS rejects builds that use location without clear usage descriptions in `Info.plist`.
- **Native dialogs.** Browser `confirm()` and `<select>` feel off in a native shell. Build small custom components instead.
- **Build pipelines.** Check your CI settings early. A single misconfiguration can silently block uploads for many builds.

None of this is hard once you know it, which is exactly why we write it down."""),
("Building software in Nigeria: what we've learned", "Practical design choices for the market we work in.", ["nigeria", "product"],
"""Building for Nigerian users changes a few design decisions:

- **Mobile first, always.** Most people meet your product on a phone. Design there first.
- **Be kind to data.** Compress images, cache sensibly, and avoid heavy pages.
- **Meet people where they are.** WhatsApp is often the fastest way to reach a customer, so put it on the page.
- **Trust is a feature.** Clear contact details, real names and real evidence (live apps, real screenshots) matter.
- **Plan for interruptions.** Connections drop. Make forms forgiving and actions safe to retry.

These aren't limitations. They're constraints that make products better for everyone."""),
("Starting a tech career in Nigeria: practical advice", "What we'd tell anyone starting out today.", ["career", "nigeria", "learning"],
"""There is no single path, but a few habits help:

1. **Build real things early.** Small projects teach more than long courses.
2. **Learn one stack deeply**, then widen. Depth gets you hired; breadth keeps you useful.
3. **Ship and show.** A live link beats a certificate. Keep a portfolio with screenshots and short case studies.
4. **Write it down.** Explaining a problem you solved proves you understood it.
5. **Find people.** Communities, mentors and collaborators multiply your progress.
6. **Be patient and consistent.** Skill compounds.

Start where you are. Ship something this week."""),
]


def seed_posts():
    base = datetime.now(timezone.utc)
    out = []
    for i, (t, ex, tags, body) in enumerate(_P):
        slug = "".join(c if c.isalnum() else "-" for c in t.lower()).strip("-")
        while "--" in slug:
            slug = slug.replace("--", "-")
        ts = base - timedelta(days=i * 3)
        out.append({"title": t, "slug": slug[:80], "excerpt": ex, "content": body, "cover": "", "tags": tags,
                    "published": True, "created": ts, "updated": ts})
    return out
