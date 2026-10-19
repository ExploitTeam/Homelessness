import { jsx as _jsx } from "/vendor/react-vendor.mjs";
import { StrictMode } from '/vendor/react-vendor.mjs';
import { createRoot } from '/vendor/react-vendor.mjs';

import App from './App.js';
createRoot(document.getElementById('root')).render(_jsx(StrictMode, { children: _jsx(App, {}) }));
