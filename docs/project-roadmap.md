# Project Roadmap — odoo-mcp

## Current State (v0.0.3)

### Completed Features

| Feature | Status | Notes |
|---------|--------|-------|
| MCP Protocol Support | ✅ Complete | FastMCP server, tools, resources |
| XML-RPC Client | ✅ Complete | Full method execution, model introspection |
| 5 MCP Tools | ✅ Complete | execute_method, search_*, search_holidays |
| 4 MCP Resources | ✅ Complete | odoo://models, model, record, search |
| Configuration | ✅ Complete | Env vars + 3 config file paths |
| Odoo 13-18 Support | ✅ Partial | Special handling for Odoo 18 (user_ids) |
| Docker Support | ✅ Complete | Python 3.10-slim, configurable |
| Claude Desktop Integration | ✅ Complete | Works with Desktop v0.4+ |
| Documentation | ✅ Complete | README + inline docstrings |

### Current Limitations

| Limitation | Impact | Workaround |
|-----------|--------|------------|
| No Async Client | Synchronous RPC blocks thread | Run multiple server instances |
| No Connection Pooling | Single connection per process | Use load balancer for scale |
| Synchronous Operations | No parallel requests | Batch operations client-side |
| Date Serialization | Manual YYYY-MM-DD strings | Always pass string dates |
| Binary Fields | Not supported | Use separate API for attachments |
| Many2many Relations | Returns ID list only | Client fetches full data if needed |
| No Caching Layer | Fresh RPC on every request | High latency for repeated queries |
| Limited Error Types | Generic ValueError/ConnectionError | Specific Odoo errors lost in translation |
| No Request Logging | Debugging requires stderr inspection | Implement structured logging |
| No Rate Limiting | No protection against abuse | Implement client-side backoff |

---

## Phase 1: Stability & Quality (Current)

**Status:** In Progress (v0.0.3)  
**Priority:** High  
**Timeline:** Q2 2024

### Goals
- Establish solid foundation for production use
- Document architecture and best practices
- Achieve type-safe, well-tested codebase

### Tasks

| Task | Status | Effort | Owner |
|------|--------|--------|-------|
| Complete documentation suite | ✅ | 1d | docs-manager |
| Add Odoo 18 compatibility | ✅ | 0.5d | code-reviewer |
| Type hints (mypy strict) | ✅ | 0.5d | code-reviewer |
| Code formatting (black) | ✅ | 0.25d | code-reviewer |
| GitHub Actions CI/CD | ⏳ | 1d | DevOps |
| Automated testing (pytest) | ⏳ | 2d | QA |

---

## Phase 2: Extended Tooling (Q3 2024)

**Status:** Planned  
**Priority:** High  
**Target Features:** 5+ new tools, better error handling

### New Tools

#### 1. search_sales_orders
```
Input: date_range, customer_name?, state?
Output: [order_id, ref, partner, total_amount, state, date]
Purpose: Quick access to sales pipelines
Odoo Model: sale.order
```

#### 2. search_invoices
```
Input: date_range, partner?, state?
Output: [invoice_id, number, partner, amount, state, date]
Purpose: Find and track invoices
Odoo Model: account.move (move_type='out_invoice')
```

#### 3. get_record_details
```
Input: model, record_id, fields?
Output: {full record with nested relations}
Purpose: Deep introspection of single record
Enhancement: Recursively resolve many2many/many2one
```

#### 4. execute_workflow
```
Input: model, record_id, button_name
Output: {success, new_state}
Purpose: Trigger state transitions, approvals
Odoo: Calls button actions on records
```

#### 5. bulk_create
```
Input: model, records[]
Output: {success, created_ids}
Purpose: Batch record creation
Optimization: Single RPC call, better performance
```

#### 6. bulk_update
```
Input: model, updates[{id, values}]
Output: {success, updated_ids}
Purpose: Batch updates with error recovery
Enhancement: Rollback support optional
```

### Improvements

| Improvement | Details | Effort |
|-------------|---------|--------|
| Better Errors | Map Odoo exceptions to specific types | 1d |
| Request Logging | Structured JSON logging to file | 0.5d |
| Rate Limiting | Backoff strategy, concurrency limits | 1d |
| Caching Layer | TTL-based cache for model metadata | 1d |
| Domain Builder | Helper to construct complex domains | 0.5d |

---

## Phase 3: Async & Performance (Q4 2024)

**Status:** Planned  
**Priority:** Medium (only if scale issues arise)

### Async Support

**Challenge:** XML-RPC stdlib doesn't support async.

**Solution:** Evaluate alternatives:
1. **aiozmq** — Async messaging (requires Odoo plugin)
2. **httpx** — Async HTTP with custom XML-RPC codec
3. **Thread pool** — Async wrapper around sync client (easier)
4. **Multiple processes** — Scale horizontally instead

**Decision:** Recommend horizontal scaling (Phase 2) before async.

### Performance Targets

| Metric | Target | Current |
|--------|--------|---------|
| P50 Latency | <100ms | ~200ms (network dependent) |
| P95 Latency | <500ms | ~1s |
| Throughput | >100 RPS | ~50 RPS (single connection) |
| Error Rate | <0.1% | ~0.5% (edge cases) |

---

## Phase 4: Advanced Features (2025)

**Status:** Conceptual  
**Priority:** Low (customer-driven)

### Potential Features

#### 1. Batch Job Support
- Schedule long-running tasks
- Progress tracking
- Retry logic
- **Effort:** 3d | **Complexity:** High

#### 2. Real-Time Subscriptions
- WebSocket-based updates (requires Odoo plugin)
- Cache invalidation on server changes
- **Effort:** 5d | **Complexity:** Very High

#### 3. Multi-Database Support
- Switch between Odoo instances
- Cross-database queries
- **Effort:** 2d | **Complexity:** Medium

#### 4. Advanced Filtering DSL
- Human-readable domain syntax
- Auto-completion support
- **Effort:** 2d | **Complexity:** Medium

#### 5. Custom Model Generation
- Schema introspection → TypeScript interfaces
- Runtime model validation
- **Effort:** 2d | **Complexity:** Medium

---

## Known Issues & Workarounds

### Issue 1: Odoo 18 Breaking Changes (user_ids)
**Status:** ✅ Fixed in v0.0.3  
**Workaround:** Automatic field detection in search_tasks

### Issue 2: Timeout on Large Queries
**Status:** ⚠️ Known limitation  
**Workaround:** Increase ODOO_TIMEOUT env var (default 30s)
```bash
ODOO_TIMEOUT=120 python -m odoo_mcp
```

### Issue 3: SSL Certificate Errors
**Status:** ⚠️ Known limitation  
**Workaround:** Disable SSL verification for testing only
```python
OdooClient(..., verify_ssl=False)  # Testing only!
```

### Issue 4: Many2many Relations Returned as IDs
**Status:** ✅ By design  
**Workaround:** Use get_record_details (planned Phase 2) for full objects

### Issue 5: No Async Support
**Status:** ⚠️ Known limitation  
**Workaround:** Deploy multiple server instances, load-balance

---

## Dependency Updates

| Dependency | Current | Latest | Status |
|-----------|---------|--------|--------|
| mcp | >=0.1.1 | 0.7+ | ✅ Monitor |
| requests | >=2.31.0 | 2.32.0 | ✅ Current |
| pypi-xmlrpc | 2020.12.3 | 2020.12.3 | ⚠️ Vendored, outdated |
| python | 3.10+ | 3.12 | ⏳ Consider upgrading |

**Action Items:**
- [ ] Test MCP 0.7+ compatibility (next release)
- [ ] Replace pypi-xmlrpc if unmaintained
- [ ] Target Python 3.12 in Phase 3

---

## Success Metrics

### Adoption
- [ ] 100+ stars on GitHub
- [ ] 10+ production deployments
- [ ] Positive user feedback in issues

### Quality
- [ ] >90% test coverage
- [ ] Zero critical security issues
- [ ] <0.1% request failure rate

### Performance
- [ ] P95 latency <500ms
- [ ] Support 100+ concurrent users
- [ ] <1% timeout rate

### Community
- [ ] 5+ GitHub contributions
- [ ] Monthly release cadence
- [ ] Active issue triage

---

## Long-Term Vision (2025+)

### Ecosystem Integration

1. **Odoo Plugin Marketplace**
   - Publish standalone MCP tools
   - Community marketplace
   - Revenue sharing model

2. **AI Agent Builder**
   - Visual workflow designer
   - Pre-built agent templates
   - Odoo-specific examples

3. **Enterprise Features**
   - Multi-tenant support
   - Audit logging
   - Advanced security (OIDC, SSO)
   - SLA guarantees

### Platform Expansion

- **Slack Integration** — Chat commands to query Odoo
- **MS Teams Bot** — Similar to Slack
- **Zapier/Make** — Low-code workflow automation
- **LangChain Plugin** — Easier AI agent development

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Odoo API Breaking Changes | Medium | High | Version detection, fallback handling |
| MCP Protocol Evolution | Medium | Medium | Regular dependency updates, CI/CD |
| Performance Degradation | Low | High | Load testing, optimization roadmap |
| Security Vulnerability | Low | Critical | Security audit, automated scanning |
| Maintenance Burden | Medium | Medium | Documentation, automated testing |
| Low Adoption | Low | Low | Marketing, community building |

---

## Maintenance & Support

### Release Cadence
- **Patch (0.0.x):** Monthly (bug fixes, security)
- **Minor (0.x.0):** Quarterly (features, improvements)
- **Major (x.0.0):** As needed (breaking changes)

### Support Lifecycle
- **v0.0.x:** 3 months support (current release)
- **v0.x.x:** 6 months support (previous major)
- **v1.0.0:** 12 months support (stable release)

### Contribution Guidelines
- Welcoming PRs for bug fixes and features
- Code review required before merge
- Backward compatibility preferred (semantic versioning)
- Documentation for all public APIs

---

## Next Steps (Immediate)

### For Users
1. Try v0.0.3 with your Odoo instance
2. Report issues on GitHub
3. Request missing features
4. Share success stories

### For Developers
1. Review code-standards.md and contribute
2. Add test coverage (see testing strategy)
3. Implement Phase 2 tools (open for community PRs)
4. Optimize performance (identify bottlenecks)

### For Maintainers
1. Finalize v0.0.3 release
2. Publish to PyPI
3. Setup GitHub Pages documentation
4. Begin Phase 2 planning with community feedback

