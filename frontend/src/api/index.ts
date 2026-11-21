import type { DataSource } from "./dataSource";
import { httpSource } from "./http";
import { mockSource } from "./mock";

/** "mock" = demo files; "api" = FastAPI server. */
export const DATA_MODE = import.meta.env.VITE_DATA_MODE === "api" ? "api" : "mock";

/** Single data source for all pages. */
export const api: DataSource = DATA_MODE === "api" ? httpSource : mockSource;