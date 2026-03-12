import { defineConfig } from "astro/config";
import { loadEnv } from "vite";

import mdx from "@astrojs/mdx";
import sitemap from "@astrojs/sitemap";
import expressiveCode from "astro-expressive-code";
import spectre from "./package/src";

import { spectreDark } from "./src/ec-theme";

// const {
//   GISCUS_REPO,
//   GISCUS_REPO_ID,
//   GISCUS_CATEGORY,
//   GISCUS_CATEGORY_ID,
//   GISCUS_MAPPING,
//   GISCUS_STRICT,
//   GISCUS_REACTIONS_ENABLED,
//   GISCUS_EMIT_METADATA,
//   GISCUS_LANG
// } = loadEnv(process.env.NODE_ENV!, process.cwd(), "");

// https://astro.build/config
const config = defineConfig({
	site: "https://ekerney.github.io",
	base: "/location-visualization",
	output: "static",
	integrations: [
		expressiveCode({
			themes: [spectreDark],
		}),
		mdx(),
		sitemap(),
		spectre({
			name: "Location Visualization",
			openGraph: {
				home: {
					title: "Location Visualization",
					description: "Location Technology & Geospatial Discussions",
				},
				blog: {
					title: "Blog",
					description: "Location Technology & Geospatial Discussions",
				},
				projects: {
					title: "Projects",
				},
			},
			// giscus: {
			//   repository: GISCUS_REPO,
			//   repositoryId: GISCUS_REPO_ID,
			//   category: GISCUS_CATEGORY,
			//   categoryId: GISCUS_CATEGORY_ID,
			//   mapping: GISCUS_MAPPING as any,
			//   strict: GISCUS_STRICT === "true",
			//   reactionsEnabled: GISCUS_REACTIONS_ENABLED === "true",
			//   emitMetadata: GISCUS_EMIT_METADATA === "true",
			//   lang: GISCUS_LANG,
			// }
		}),
	],
});

export default config;
