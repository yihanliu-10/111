# Lean 4 check of Appendix A.1 (CT Gaussian Splatting paper)

`LeanCheck/Appendix.lean` machine-checks the algebraic content of Appendix A.1 of
"Fewer and Safer: Group-Relative Simplification via Convex Density Optimization for
CT Gaussian Splatting" (ICLR 2027 submission draft), stated over any linearly
ordered field (so ℝ is a special case):

| Paper | Lean theorem |
|---|---|
| A.1.1 linearity in density | `CTGS.proj_linear` |
| A.1.1 column decomposition ŷ = Σ ρᵢ A:,i | `CTGS.proj_eq_sum_columns` |
| A.1.1 removing Gaussian i deletes one column | `CTGS.proj_remove` |
| Eq. (10) | `CTGS.cost_expand` |
| Lemma 1, bounds 0 ≤ C(S) ≤ ½‖y‖² | `CTGS.minimizer_bounds` |
| Eq. (11) | `CTGS.cost_midpoint` |
| Lemma 2 (fitted projection unique) | `CTGS.fitted_projection_unique` |
| Δ(a) well defined | `CTGS.action_cost_well_defined` |
| Example A = [1 1], y = 1 | `CTGS.example_minimizer`, `CTGS.example_not_unique` |

Not formalized: the existence half of Lemma 1 (needs closedness of finitely
generated cones over ℝ, not in Mathlib) and the calculus facts ∇f, ∇²f.

## Build

```bash
# Lean toolchain from lean-toolchain; Mathlib pinned in lakefile.toml
lake exe cache get   # if the Mathlib cache is reachable
lake build           # otherwise compiles ~1300 Mathlib modules first
```

Expected output ends with `Build completed successfully` and five
`#print axioms` lines listing only `propext`, `Classical.choice`, `Quot.sound`.
