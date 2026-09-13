import Mathlib.LinearAlgebra.Matrix.DotProduct
import Mathlib.LinearAlgebra.Matrix.Notation
import Mathlib.Algebra.Order.Field.Basic
import Mathlib.Tactic.Ring
import Mathlib.Tactic.Linarith
import Mathlib.Tactic.FinCases
import Mathlib.Tactic.Positivity

/-!
# Machine-checked verification of Appendix A.1 of
# "Fewer and Safer: Group-Relative Simplification via Convex Density Optimization
#  for CT Gaussian Splatting" (ICLR 2027 submission draft)

Everything is stated over an arbitrary linearly ordered field `𝕜` (so `ℝ` is a special
case).  Vectors are functions `K → 𝕜` / `N → 𝕜`, the projection operator is the matrix
`A : Matrix K N 𝕜` from Eq. (6), `A *ᵥ ρ` is `Aρ`, and `‖v‖²` is written `v ⬝ᵥ v`.

Scope:
* Appendix A.1.1 (linearity in density, column decomposition, removing a Gaussian).
* Eq. (10) (the expansion of `f(ρ + Δ)`).
* Lemma 1's bounds `0 ≤ C(S) ≤ ½‖y‖²`.
* Eq. (11) (the midpoint identity) and Lemma 2 (all minimizers give the same `Aρ`).
* The non-uniqueness example `A = [1 1]`, `y = 1`.
* Well-definedness of the action cost `Δ(a) = C(S_a) − C(S)`.

Not covered: the *existence* half of Lemma 1 (a topological statement about `ℝ`:
finitely generated cones are closed), and the calculus facts `∇f`, `∇²f`.
-/

open Matrix

namespace CTGS

variable {𝕜 : Type*} [Field 𝕜] [LinearOrder 𝕜] [IsStrictOrderedRing 𝕜]
variable {K N : Type*} [Fintype K] [Fintype N]

/-- `‖v‖² = v ⬝ᵥ v ≥ 0`. -/
theorem dotProduct_self_nonneg (v : K → 𝕜) : 0 ≤ v ⬝ᵥ v :=
  Fintype.sum_nonneg fun _ => mul_self_nonneg _

/-! ## Appendix A.1.1 — linearity of the projection in density under fixed geometry -/

/-- `ŷ(sρ + s'ρ') = s ŷ(ρ) + s' ŷ(ρ')`. -/
theorem proj_linear (A : Matrix K N 𝕜) (s s' : 𝕜) (ρ ρ' : N → 𝕜) :
    A *ᵥ (s • ρ + s' • ρ') = s • (A *ᵥ ρ) + s' • (A *ᵥ ρ') := by
  simp [Matrix.mulVec_add, Matrix.mulVec_smul]

/-- Column decomposition `ŷ = Σᵢ ρᵢ A_{:,i}`. -/
theorem proj_eq_sum_columns (A : Matrix K N 𝕜) (ρ : N → 𝕜) :
    A *ᵥ ρ = ∑ i, ρ i • A.col i := by
  ext k
  simp [Matrix.mulVec, dotProduct, Finset.sum_apply, mul_comm]

/-- Setting `ρᵢ = 0` (removing Gaussian `i`) deletes exactly the term `ρᵢ A_{:,i}`;
all other columns are untouched. -/
theorem proj_remove [DecidableEq N] (A : Matrix K N 𝕜) (ρ : N → 𝕜) (i : N) :
    A *ᵥ (Function.update ρ i 0) = A *ᵥ ρ - ρ i • A.col i := by
  have h : Function.update ρ i 0 = ρ - ρ i • Pi.single i 1 := by
    ext j
    by_cases hj : j = i
    · subst hj; simp
    · simp [Function.update_of_ne hj, Pi.single_apply, hj]
  rw [h, Matrix.mulVec_sub, Matrix.mulVec_smul, Matrix.mulVec_single_one]

/-! ## Section 4.1 — the density cost -/

/-- Eq. (7): `f_S(ρ) = ½ ‖y − A_S ρ‖²`. -/
def cost (A : Matrix K N 𝕜) (y : K → 𝕜) (ρ : N → 𝕜) : 𝕜 :=
  (1 / 2) * ((y - A *ᵥ ρ) ⬝ᵥ (y - A *ᵥ ρ))

/-- The feasible set `ρ ≥ 0` of Eq. (8). -/
def Feasible (ρ : N → 𝕜) : Prop := ∀ i, 0 ≤ ρ i

/-- `ρ⋆` attains the minimum in Eq. (8). -/
def IsMinimizer (A : Matrix K N 𝕜) (y : K → 𝕜) (ρ⋆ : N → 𝕜) : Prop :=
  Feasible ρ⋆ ∧ ∀ ρ, Feasible ρ → cost A y ρ⋆ ≤ cost A y ρ

theorem feasible_zero : Feasible (0 : N → 𝕜) := fun _ => le_rfl

theorem cost_nonneg (A : Matrix K N 𝕜) (y : K → 𝕜) (ρ : N → 𝕜) : 0 ≤ cost A y ρ :=
  mul_nonneg (by norm_num) (dotProduct_self_nonneg _)

theorem cost_zero (A : Matrix K N 𝕜) (y : K → 𝕜) : cost A y 0 = (1 / 2) * (y ⬝ᵥ y) := by
  simp [cost]

/-! ## Appendix A.1.2, "Standard facts" — Eq. (10) -/

/-- Eq. (10): `f(ρ + Δ) = f(ρ) + ⟨Aᵀ(Aρ − y), Δ⟩ + ½‖AΔ‖²`. -/
theorem cost_expand (A : Matrix K N 𝕜) (y : K → 𝕜) (ρ Δ : N → 𝕜) :
    cost A y (ρ + Δ) =
      cost A y ρ + (Aᵀ *ᵥ (A *ᵥ ρ - y)) ⬝ᵥ Δ + (1 / 2) * ((A *ᵥ Δ) ⬝ᵥ (A *ᵥ Δ)) := by
  unfold cost
  have h1 : (Aᵀ *ᵥ (A *ᵥ ρ - y)) ⬝ᵥ Δ = (A *ᵥ ρ - y) ⬝ᵥ (A *ᵥ Δ) := by
    rw [Matrix.mulVec_transpose, ← Matrix.dotProduct_mulVec]
  rw [h1, Matrix.mulVec_add]
  set r := y - A *ᵥ ρ with hr
  have h2 : y - (A *ᵥ ρ + A *ᵥ Δ) = r - A *ᵥ Δ := by rw [hr]; abel
  have h3 : A *ᵥ ρ - y = -r := by rw [hr]; abel
  rw [h2, h3]
  simp only [sub_dotProduct, dotProduct_sub, neg_dotProduct, dotProduct_comm (A *ᵥ Δ) r]
  ring

/-! ## Lemma 1 — the bounds `0 ≤ C(S) ≤ ½‖y‖²` (existence is not formalized here) -/

theorem minimizer_bounds {A : Matrix K N 𝕜} {y : K → 𝕜} {ρ⋆ : N → 𝕜}
    (h : IsMinimizer A y ρ⋆) :
    0 ≤ cost A y ρ⋆ ∧ cost A y ρ⋆ ≤ (1 / 2) * (y ⬝ᵥ y) :=
  ⟨cost_nonneg A y ρ⋆, by rw [← cost_zero A y]; exact h.2 0 feasible_zero⟩

/-! ## Lemma 2 — Eq. (11) and uniqueness of the fitted projection -/

/-- Eq. (11): with `ρ̄ = (ρ⁽¹⁾ + ρ⁽²⁾)/2`,
`f(ρ̄) = ½[f(ρ⁽¹⁾) + f(ρ⁽²⁾)] − ⅛ ‖A(ρ⁽¹⁾ − ρ⁽²⁾)‖²`. -/
theorem cost_midpoint (A : Matrix K N 𝕜) (y : K → 𝕜) (ρ₁ ρ₂ : N → 𝕜) :
    cost A y ((1 / 2 : 𝕜) • (ρ₁ + ρ₂)) =
      (1 / 2) * (cost A y ρ₁ + cost A y ρ₂)
        - (1 / 8) * ((A *ᵥ (ρ₁ - ρ₂)) ⬝ᵥ (A *ᵥ (ρ₁ - ρ₂))) := by
  unfold cost
  set r₁ := y - A *ᵥ ρ₁ with hr₁
  set r₂ := y - A *ᵥ ρ₂ with hr₂
  have h1 : y - A *ᵥ ((1 / 2 : 𝕜) • (ρ₁ + ρ₂)) = (1 / 2 : 𝕜) • (r₁ + r₂) := by
    rw [Matrix.mulVec_smul, Matrix.mulVec_add, hr₁, hr₂]
    ext k
    simp only [Pi.sub_apply, Pi.add_apply, Pi.smul_apply, smul_eq_mul]
    ring
  have h2 : A *ᵥ (ρ₁ - ρ₂) = r₂ - r₁ := by
    rw [Matrix.mulVec_sub, hr₁, hr₂]; abel
  rw [h1, h2]
  simp only [smul_dotProduct, dotProduct_smul, add_dotProduct, dotProduct_add, sub_dotProduct,
    dotProduct_sub, smul_eq_mul, dotProduct_comm r₂ r₁]
  ring

/-- Midpoint convexity of the cost (a corollary of Eq. (11)). -/
theorem cost_midpoint_le (A : Matrix K N 𝕜) (y : K → 𝕜) (ρ₁ ρ₂ : N → 𝕜) :
    cost A y ((1 / 2 : 𝕜) • (ρ₁ + ρ₂)) ≤ (1 / 2) * (cost A y ρ₁ + cost A y ρ₂) := by
  rw [cost_midpoint]
  have := dotProduct_self_nonneg (A *ᵥ (ρ₁ - ρ₂))
  linarith

/-- The optimal value is the same for every minimizer (trivial, but this is all the
final paragraph of A.1.2 actually needs). -/
theorem minimizer_cost_eq {A : Matrix K N 𝕜} {y : K → 𝕜} {ρ₁ ρ₂ : N → 𝕜}
    (h₁ : IsMinimizer A y ρ₁) (h₂ : IsMinimizer A y ρ₂) :
    cost A y ρ₁ = cost A y ρ₂ :=
  le_antisymm (h₁.2 _ h₂.1) (h₂.2 _ h₁.1)

/-- Lemma 2: any two minimizers of Eq. (8) produce the same fitted projection
`Aρ⁽¹⁾ = Aρ⁽²⁾`.  This follows the paper's midpoint argument line by line. -/
theorem fitted_projection_unique {A : Matrix K N 𝕜} {y : K → 𝕜} {ρ₁ ρ₂ : N → 𝕜}
    (h₁ : IsMinimizer A y ρ₁) (h₂ : IsMinimizer A y ρ₂) :
    A *ᵥ ρ₁ = A *ᵥ ρ₂ := by
  -- the midpoint is feasible
  have hmid : Feasible ((1 / 2 : 𝕜) • (ρ₁ + ρ₂)) := by
    intro i
    have := h₁.1 i
    have := h₂.1 i
    simp only [Pi.smul_apply, Pi.add_apply, smul_eq_mul]
    positivity
  -- so its cost is at least the minimum
  have hge := h₁.2 _ hmid
  rw [cost_midpoint, minimizer_cost_eq h₁ h₂] at hge
  -- Eq. (11) then forces ‖A(ρ₁ − ρ₂)‖² = 0
  have hq0 := dotProduct_self_nonneg (A *ᵥ (ρ₁ - ρ₂))
  have hq : (A *ᵥ (ρ₁ - ρ₂)) ⬝ᵥ (A *ᵥ (ρ₁ - ρ₂)) = 0 := by linarith
  have := dotProduct_self_eq_zero.mp hq
  rw [Matrix.mulVec_sub] at this
  exact sub_eq_zero.mp this

/-- The action cost `Δ(a) = C(S_a) − C(S)` does not depend on which optimal density
vectors are chosen for `S` and `S_a`. -/
theorem action_cost_well_defined
    {N' : Type*} [Fintype N'] {A : Matrix K N 𝕜} {A' : Matrix K N' 𝕜} {y : K → 𝕜}
    {ρ₁ ρ₂ : N → 𝕜} {σ₁ σ₂ : N' → 𝕜}
    (h₁ : IsMinimizer A y ρ₁) (h₂ : IsMinimizer A y ρ₂)
    (g₁ : IsMinimizer A' y σ₁) (g₂ : IsMinimizer A' y σ₂) :
    cost A' y σ₁ - cost A y ρ₁ = cost A' y σ₂ - cost A y ρ₂ := by
  rw [minimizer_cost_eq h₁ h₂, minimizer_cost_eq g₁ g₂]

/-! ## The non-uniqueness example: `A = [1 1]`, `y = 1` -/

/-- For every `t ∈ [0,1]`, `ρ = (t, 1 − t)` is feasible, fits exactly (`Aρ = 1`), and is
therefore a minimizer with cost `0`. -/
theorem example_minimizer (t : 𝕜) (ht0 : 0 ≤ t) (ht1 : t ≤ 1) :
    (!![1, 1] : Matrix (Fin 1) (Fin 2) 𝕜) *ᵥ ![t, 1 - t] = ![1] ∧
      IsMinimizer (!![1, 1] : Matrix (Fin 1) (Fin 2) 𝕜) ![1] ![t, 1 - t] := by
  have hfit : (!![1, 1] : Matrix (Fin 1) (Fin 2) 𝕜) *ᵥ ![t, 1 - t] = ![1] := by
    ext i
    fin_cases i
    simp [Matrix.mulVec, dotProduct, Fin.sum_univ_two]
  refine ⟨hfit, ?_, ?_⟩
  · intro i
    fin_cases i <;> simp <;> linarith
  · intro ρ _
    have : cost (!![1, 1] : Matrix (Fin 1) (Fin 2) 𝕜) ![1] ![t, 1 - t] = 0 := by
      simp [cost, hfit]
    rw [this]
    exact cost_nonneg _ _ _

/-- Two *different* density vectors are both minimizers: the minimizer is not unique,
even though (by Lemma 2) the fitted projection is. -/
theorem example_not_unique :
    IsMinimizer (!![1, 1] : Matrix (Fin 1) (Fin 2) 𝕜) ![1] ![0, 1] ∧
      IsMinimizer (!![1, 1] : Matrix (Fin 1) (Fin 2) 𝕜) ![1] ![1, 0] ∧
      (![0, 1] : Fin 2 → 𝕜) ≠ ![1, 0] := by
  refine ⟨?_, ?_, ?_⟩
  · have h := (example_minimizer (𝕜 := 𝕜) 0 le_rfl zero_le_one).2
    simpa using h
  · have h := (example_minimizer (𝕜 := 𝕜) 1 zero_le_one le_rfl).2
    simpa using h
  · intro h
    have := congrFun h 0
    simp at this

end CTGS

#print axioms CTGS.proj_remove
#print axioms CTGS.cost_expand
#print axioms CTGS.cost_midpoint
#print axioms CTGS.fitted_projection_unique
#print axioms CTGS.example_not_unique
