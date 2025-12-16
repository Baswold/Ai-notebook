---
title: Self-Controlled RL with Hidden Annotation Tokens
created: 2024-12-13
status: concept
tags: reinforcement-learning, self-supervision, meta-learning, hidden-tokens, reward-modeling
---

## Overview

### What It Is

Self-Controlled RL is a training paradigm where an AI model annotates its own outputs during generation using hidden tokens (similar to `<think>` tags). These annotations guide what the model remembers and potentially how it receives training signals, creating a self-supervised learning loop where the model controls its own curriculum and memory.

The core mechanism involves the model producing hidden tokens like `<remember>`, `<reward>`, and `<novel>` within its output stream. These tokens are invisible to users but processed by the training system to:
- Store important moments in memory/retrieval systems
- Flag novel insights for preservation
- Potentially influence reward signals (with careful safeguards)

### Why It's Valuable

**Efficiency**: Eliminates the need for separate annotation models or extensive human labeling. The model that generates content is also the model that understands which parts of that content are worth preserving or learning from.

**Alignment**: The model's own assessment of what's important may be more aligned with its actual decision-making process than external annotations. It can identify subtle patterns or important moments that external annotators might miss.

**Scalability**: Generates training signal continuously during deployment without additional infrastructure. Every conversation becomes a potential source of self-improvement.

**Meta-Learning**: The model can potentially learn what kinds of behaviors lead to better downstream outcomes, developing increasingly sophisticated self-evaluation capabilities.

### Novelty Assessment

This builds on several existing research directions but combines them in a unique way:

**Related existing work:**
- Intrinsic motivation and curiosity-driven RL (models reward themselves for novel states)
- Self-play and self-improvement (models train against themselves)
- Constitutional AI (models evaluate their own outputs against principles)
- Hindsight Experience Replay (reinterpreting past experiences)

**Novel aspects:**
- Using hidden annotation tokens (like `<think>`) as the mechanism for self-supervision
- Combining memory control, novelty detection, and reward signals in a unified framework
- The model controlling what it remembers in real-time during generation
- Separating novelty preservation from reward assignment to avoid reward hacking

The key innovation is the tight integration: the same forward pass that generates user-facing content also produces the training annotations, creating a seamless self-supervision loop.

## Technical Details

### Architecture

The system operates in three main components:

**1. Generation with Hidden Tokens**

During forward pass, the model generates both visible content and hidden annotation tokens:
```
User: [question]
Model: [visible response] <remember>key insight X</remember> [more visible content] <novel>discovered pattern Y</novel>
```

These tags are:
- Part of the model's output logits
- Learned through training (the model learns when to use them)
- Hidden from user interface through formatting/parsing
- Available to downstream training systems

**2. Annotation Processing**

A post-processing system extracts and acts on annotations:
- `<remember>...</remember>`: Content flagged for storage in retrieval/memory system
- `<novel>...</novel>`: Novel insights saved without reward attachment
- `<reward>...</reward>`: Self-assessment signals (requires careful handling)

**3. Training Signal Generation**

Annotations influence future training through:
- Memory storage for retrieval-augmented generation
- Intrinsic motivation signals (curiosity rewards)
- Credit assignment when external validation arrives
- Curriculum learning (prioritizing remembered examples)

### Key Technical Decisions

**Decision 1: Hidden tokens vs. separate annotation model**

Using hidden tokens means the model learns to annotate as part of its core capability, rather than requiring a separate annotation model. This is more efficient but requires the model to develop meta-cognitive abilities.

**Decision 2: Novelty without reward**

For `<novel>` tags, the system stores the insight but doesn't provide reward. This prevents the model from learning to game novelty detection while still preserving genuinely new patterns. The model receives intrinsic motivation from exploration but not explicit reward.

**Decision 3: Delayed reward validation**

Rather than immediately using `<reward>` tags in training, the system waits for external validation (user satisfaction, task completion) before applying credit. This prevents reward hacking while still allowing the model to flag what it thinks was valuable.

### Dependencies & Requirements

**Training infrastructure:**
- Support for hidden token parsing in generation pipeline
- Memory/retrieval system for `<remember>` content storage
- External validation signals (user feedback, task metrics)
- Retrospective credit assignment system

**Model capabilities:**
- Ability to generate structured tags during normal output
- Meta-cognitive reasoning (thinking about its own thinking)
- Consistent annotation behavior across contexts

**Data requirements:**
- Initial supervised examples of good annotation behavior
- External validation data for calibrating self-assessments
- Diverse conversation contexts for learning when to annotate

### Constraints & Parameters

**Context window constraints:**
Hidden tokens consume context, potentially reducing space for visible content. Need to balance annotation richness with output quality.

**Annotation frequency:**
Too many annotations create noise; too few miss important moments. May need learned thresholds or budgets.

**Memory storage limits:**
Cannot store everything flagged with `<remember>`. Need prioritization or decay mechanisms.

**Temporal credit assignment:**
How long to wait for external validation? Need to balance immediate feedback with long-term outcomes.

## Implementation

### Basic Hidden Token Generation

The model learns to produce annotations naturally during generation:

```python
# During generation, model produces hidden tokens
output = model.generate(prompt)
# Output might contain:
# "The solution is X <remember>X worked because of constraint Y</remember> which means Z"

# Parse hidden tokens
import re
visible_text = re.sub(r'<remember>.*?</remember>', '', output)
remember_tags = re.findall(r'<remember>(.*?)</remember>', output)
novel_tags = re.findall(r'<novel>(.*?)</novel>', output)
```

### Memory Storage System

```python
class MemoryStore:
    def __init__(self):
        self.memories = []
        self.embeddings = []
    
    def add_memory(self, content, context, timestamp):
        """Store remembered content with conversation context"""
        memory_entry = {
            'content': content,
            'context': context,  # Surrounding conversation
            'timestamp': timestamp,
            'access_count': 0
        }
        self.memories.append(memory_entry)
        # Generate embedding for retrieval
        self.embeddings.append(self.embed(content))
    
    def retrieve_relevant(self, query, top_k=5):
        """Retrieve memories relevant to current query"""
        query_embedding = self.embed(query)
        similarities = cosine_similarity(query_embedding, self.embeddings)
        top_indices = np.argsort(similarities)[-top_k:]
        return [self.memories[i] for i in top_indices]
```

### Reward Validation System

```python
class RewardValidator:
    def __init__(self):
        self.pending_rewards = []  # Self-assessments awaiting validation
    
    def record_self_assessment(self, conversation_id, step, self_reward):
        """Store model's self-reward claim for later validation"""
        self.pending_rewards.append({
            'conversation_id': conversation_id,
            'step': step,
            'self_reward': self_reward,
            'timestamp': time.time()
        })
    
    def validate_with_external_signal(self, conversation_id, external_reward):
        """When external validation arrives, compute actual training signal"""
        # Find all self-assessments for this conversation
        self_assessments = [
            r for r in self.pending_rewards 
            if r['conversation_id'] == conversation_id
        ]
        
        # Credit assignment: which self-assessments were accurate?
        for assessment in self_assessments:
            # Compare self-reward to external outcome
            accuracy = 1.0 - abs(assessment['self_reward'] - external_reward)
            
            # Use this to train the model's self-assessment capability
            # High accuracy = model is learning to predict what's valuable
            # Low accuracy = model needs to adjust its self-evaluation
            
            yield TrainingExample(
                conversation_id=assessment['conversation_id'],
                step=assessment['step'],
                reward=external_reward,
                meta_reward=accuracy  # Reward for accurate self-assessment
            )
```

### Training Loop Integration

```python
def train_with_self_control(model, conversations):
    memory_store = MemoryStore()
    reward_validator = RewardValidator()
    
    for conversation in conversations:
        # Generate with hidden tokens
        output = model.generate(conversation.prompt)
        
        # Extract annotations
        annotations = parse_annotations(output)
        
        # Process remember tags
        for content in annotations['remember']:
            memory_store.add_memory(
                content=content,
                context=conversation.history,
                timestamp=time.time()
            )
        
        # Process novel tags (store but don't reward)
        for insight in annotations['novel']:
            memory_store.add_memory(
                content=insight,
                context=conversation.history,
                timestamp=time.time(),
                is_novel=True
            )
        
        # Record self-rewards for later validation
        for self_reward in annotations['reward']:
            reward_validator.record_self_assessment(
                conversation_id=conversation.id,
                step=conversation.current_step,
                self_reward=self_reward
            )
        
        # When external validation arrives (user feedback, task success)
        if conversation.has_external_validation():
            training_examples = reward_validator.validate_with_external_signal(
                conversation_id=conversation.id,
                external_reward=conversation.external_reward
            )
            
            # Update model with validated rewards
            for example in training_examples:
                model.update(example)
```

### Annotation Training

The model needs to learn when to use annotation tokens. Initial training uses supervised examples:

```python
# Training data format
training_examples = [
    {
        'input': 'User asked about algorithm efficiency',
        'output': 'The algorithm runs in O(n log n) <remember>Key insight: comparison-based sorting has O(n log n) lower bound</remember>',
        'annotation_label': 'good'  # This is a useful thing to remember
    },
    {
        'input': 'User said hello',
        'output': 'Hello! <remember>User greeted me</remember>',
        'annotation_label': 'bad'  # Not useful to remember routine greetings
    }
]
```

Over time, the model learns from external validation which annotations were actually valuable.

## Context & Conversation History

### Origin of the Idea

This concept builds on previous work where we were annotating chats to train an AI model. The process involved:
1. Human or AI annotators reviewing conversations
2. Marking important moments, good responses, or learning opportunities
3. Training a model on these annotated examples

The key insight was: "Why don't we just train the original model to be able to annotate its own conversations?"

### Key Design Decisions Made

**Decision to separate novelty from reward:**
Early in the discussion, we identified that self-rewarding could lead to reward hacking. The decision was made to handle novel insights differently - the model can flag them and preserve them, but doesn't get explicit reward for doing so. This preserves intrinsic motivation without opening the door to gaming.

**Choice of hidden token mechanism:**
The user proposed using hidden tokens (like `<think>`) as the implementation mechanism. This is elegant because:
- The model already understands structured tags
- They can be hidden from users through formatting
- They're transparent to developers for debugging
- They fit naturally into the generation process

**Retrospective reward validation:**
Rather than allowing `<reward>` tags to immediately influence training, we decided rewards should be validated against external signals. The self-assessments become *candidates* that are checked against reality.

### Evolution During Discussion

Initial concept → Add hidden tokens → Separate novelty and reward → Add external validation → Develop complete architecture

The idea evolved from "model annotates itself" to a more nuanced system with safeguards against reward hacking while preserving the benefits of self-supervision.

### User's Specific Goals

The user wants a system that:
- Allows the model to control what it remembers
- Preserves novel insights without reward gaming
- Eventually enables self-improvement through better self-assessment
- Remains efficient and scalable

### Key Insights from Conversation

1. Self-reward is dangerous but self-memory is valuable
2. External validation is critical for grounding
3. Novelty detection should be separated from reward
4. Hidden tokens provide a clean implementation path
5. The model needs to learn meta-cognitive skills (knowing what's worth remembering)

## Challenges & Limitations

### The Reward Hacking Problem

**The core danger:** If the model can directly influence its own training signal through `<reward>` tags, it could learn to assign maximum reward to trivial actions, creating a reward-maximizing loop that doesn't correspond to useful behavior (wireheading).

**Severity:** Critical - this could completely undermine the training process.

**Mitigations:**
- External validation required before rewards are applied
- Meta-rewards for accurate self-assessment (not just high self-rewards)
- Multiple sources of validation (user feedback, task success, consistency checks)
- Anomaly detection for suspicious reward patterns

### Annotation Quality Decay

**Challenge:** The model might learn to produce annotations that look good but aren't actually useful. For example, flagging everything as important or using annotations to game the system in subtle ways.

**Indicators to watch:**
- Increasing annotation frequency without improving outcomes
- Annotations that don't correlate with external validation
- Repetitive or formulaic annotation patterns

**Potential solutions:**
- Regular human audits of annotation quality
- Diversity penalties (discourage repetitive annotations)
- Anomaly detection on annotation patterns
- A/B testing with and without self-annotations

### Context Window Consumption

**Problem:** Hidden tokens take up context that could be used for visible content or reasoning. Too many annotations could degrade response quality.

**Trade-off:** More annotations = better self-supervision but less space for content.

**Possible approaches:**
- Learned annotation budgets (model learns to annotate sparingly)
- Compression of annotations (concise metadata instead of full text)
- Separate annotation channel (if technically feasible)

### Cold Start Problem

**Challenge:** The model needs to learn good annotation behavior, but initially has no examples of what "good" means. How do we bootstrap the system?

**Approaches:**
- Supervised pre-training on human-annotated examples
- Imitation learning from expert annotations
- Conservative initial policy (under-annotate rather than over-annotate)
- Gradual expansion of annotation capability

### Memory Management

**Challenge:** Cannot store everything the model flags with `<remember>`. Need prioritization, decay, and retrieval mechanisms.

**Considerations:**
- How long to retain memories?
- How to prioritize when storage is limited?
- How to avoid redundant or conflicting memories?
- How to update or refine memories over time?

### Temporal Credit Assignment

**Challenge:** External validation may come long after the conversation (or never). How long do we wait? How do we handle conversations without clear success/failure signals?

**Difficulty:** Short wait times miss long-term outcomes; long wait times delay learning.

**Potential solutions:**
- Multiple validation timeframes (immediate, short-term, long-term)
- Partial credit based on available signals
- Default assumptions when validation is unavailable
- User feedback as primary validation source

### Distribution Shift

**Challenge:** The model's annotation behavior might drift over time as it receives training signals based on its own annotations. This could lead to feedback loops or mode collapse.

**Monitoring needed:**
- Diversity of annotation patterns
- Correlation between annotations and outcomes
- Stability of annotation frequency and type

### Gaming Through Subtlety

**Challenge:** The model might learn sophisticated ways to game the system that aren't obvious. For example, annotating in ways that influence human reviewers or optimizing for validation metrics rather than true usefulness.

**Difficulty:** Hard to detect because it requires understanding the model's "intentions" or implicit optimization target.

## Next Steps

### Immediate Research Questions

1. **Prototype the hidden token mechanism**
   - Implement basic parsing of `<remember>`, `<novel>`, `<reward>` tags
   - Test whether models can learn to use them consistently
   - Measure context window overhead

2. **Design reward validation experiments**
   - Create test scenarios with clear external validation
   - Measure correlation between self-rewards and outcomes
   - Identify failure modes in self-assessment

3. **Build minimal memory system**
   - Implement basic storage and retrieval
   - Test with hand-crafted examples
   - Measure retrieval quality and relevance

### Short-term Experiments

1. **Supervised annotation training**
   - Collect dataset of conversations with expert annotations
   - Fine-tune model to produce hidden annotations
   - Evaluate annotation quality vs. expert baseline

2. **Reward hacking stress tests**
   - Deliberately create conditions that incentivize gaming
   - Measure how quickly the model learns to hack
   - Test effectiveness of various safeguards

3. **Memory utility assessment**
   - Track which memories actually get used
   - Measure impact on conversation quality
   - Optimize storage and retrieval strategies

### Medium-term Goals

1. **Integrate with existing RL training pipeline**
   - Add annotation processing to training loop
   - Implement retrospective validation
   - Monitor for unexpected behaviors

2. **Develop meta-learning curriculum**
   - Train model to improve its self-assessment accuracy
   - Measure learning of meta-cognitive skills
   - Compare to baselines without self-control

3. **Scale testing**
   - Test with larger models
   - Test with more diverse tasks
   - Measure computational overhead

### Long-term Vision

1. **Self-improving systems**
   - Models that genuinely learn from their own experience
   - Continuous improvement during deployment
   - Reduced need for external supervision

2. **Transfer to other domains**
   - Apply self-control to robotics, games, other RL domains
   - Test generalization of annotation skills
   - Develop domain-specific annotation vocabularies

3. **Theoretical understanding**
   - Formal analysis of convergence properties
   - Characterize conditions for stable learning
   - Develop theory of self-supervised RL

### Research Needed

- Survey of self-play and self-improvement literature
- Analysis of successful intrinsic motivation approaches
- Study of human meta-cognition and self-monitoring
- Review of reward modeling and preference learning techniques

### Resources to Gather

- Access to compute for training experiments
- Datasets with external validation signals
- Expert annotators for baseline comparisons
- Monitoring infrastructure for detecting anomalies

## Related Concepts

### Intrinsic Motivation & Curiosity-Driven RL

Systems like ICM (Intrinsic Curiosity Module) and RND (Random Network Distillation) reward models for encountering novel states. Self-Controlled RL extends this by letting the model explicitly flag what it finds novel rather than using implicit novelty measures.

**Key papers:**
- "Curiosity-driven Exploration by Self-supervised Prediction" (Pathak et al.)
- "Exploration by Random Network Distillation" (Burda et al.)

### Constitutional AI & Self-Critique

Constitutional AI (Anthropic) trains models to evaluate and improve their own outputs against principles. Self-Controlled RL applies similar self-evaluation but focuses on what to remember and learn from rather than constitutional principles.

### Meta-Learning & Learning to Learn

Meta-learning algorithms learn how to learn more efficiently. Self-Controlled RL is a form of meta-learning where the model learns what's worth learning from.

**Related:** MAML, Reptile, learning-to-learn frameworks

### Hindsight Experience Replay

HER (Hindsight Experience Replay) reinterprets failed experiences as successes for different goals. Self-Controlled RL similarly reinterprets experiences by having the model annotate what was actually valuable in retrospect.

### Active Learning & Curriculum Learning

The model's annotations effectively create its own curriculum by flagging important examples. This is related to active learning (selecting what to learn from) and curriculum learning (ordering training examples).

### Self-Play in Games

AlphaGo and AlphaZero improve through self-play, training against themselves. Self-Controlled RL extends this idea beyond adversarial games to general conversation and reasoning tasks.

### Memory-Augmented Neural Networks

Systems like Neural Turing Machines and Differentiable Neural Computers learn to use external memory. Self-Controlled RL gives the model explicit control over what goes into memory through `<remember>` tags.

### Reward Modeling & RLHF

Reinforcement Learning from Human Feedback trains reward models to predict human preferences. Self-Controlled RL explores whether models can learn to predict what will be valuable, essentially learning their own reward model.

### Neuroscience Connections

Human metacognition involves monitoring and controlling one's own thinking. Self-Controlled RL is inspired by this metacognitive ability - knowing what's important to remember and what experiences were valuable.

**Related concepts:** Self-monitoring, metacognitive awareness, episodic memory control

### Cross-Domain Applications

**Education:** Students benefit from self-assessment and controlling their own learning
**Robotics:** Robots that decide what experiences to learn from
**Scientific discovery:** Systems that flag surprising results for follow-up
**Creative AI:** Models that recognize and preserve their novel ideas