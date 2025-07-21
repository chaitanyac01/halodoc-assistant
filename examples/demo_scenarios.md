# 🎯 Halodoc AI Assistant - Demo Scenarios

## Scenario 1: Service Discovery Flow
**Objective**: Demonstrate RAG-powered FAQ handling

```
User: What homecare services does Halodoc provide?
→ Orchestrator routes to Discovery Agent
→ Discovery Agent searches vector DB
→ Returns comprehensive service list

User: How much does a nurse visit cost?
→ Discovery Agent provides pricing information

User: What's included in the elderly care package?
→ Discovery Agent retrieves specific package details
```

## Scenario 2: Medical Consultation → Booking
**Objective**: Show agent handoff and booking flow

```
User: I've been having severe knee pain for 2 weeks. It hurts when I walk.
→ Orchestrator routes to Medical Advisor
→ Medical Advisor analyzes symptoms
→ Recommends physiotherapy service

User: Yes, I'd like to book a physiotherapy session
→ Handoff to Booking Agent
→ Booking Agent initiates booking flow

User: Tomorrow at 3 PM
→ Booking Agent confirms datetime

User: 123 MG Road, Bangalore
→ Booking Agent generates payment link

User: paid
→ Booking confirms order
→ Handoff to Care Navigator
```

## Scenario 3: Existing Customer Support
**Objective**: Demonstrate post-booking support

```
User: I have a nurse visit scheduled tomorrow. What should I prepare?
→ Orchestrator routes to Care Navigator
→ Care Navigator provides preparation checklist

User: Can I reschedule to day after tomorrow?
→ Care Navigator checks policy
→ Processes rescheduling

User: Track my order HD-20240125-ABC123
→ Care Navigator provides real-time status
```

## Scenario 4: Complex Medical Query
**Objective**: Show medical advisor capabilities

```
User: My elderly mother has diabetes and recently had knee surgery. She needs regular wound dressing and physiotherapy. What services should we get?
→ Medical Advisor analyzes multiple conditions
→ Recommends combination of services
→ Offers to connect with booking
```

## Scenario 5: Emergency Handling
**Objective**: Demonstrate safety protocols

```
User: I'm having severe chest pain and difficulty breathing
→ Medical Advisor detects emergency keywords
→ Immediately recommends emergency services
→ Still offers non-emergency alternatives
```

## Demo Tips

### For Maximum Impact:
1. **Start with Discovery**: Show how it retrieves FAQ information
2. **Transition to Medical**: Demonstrate intelligent symptom analysis
3. **Complete a Booking**: Show the full E2E flow
4. **Show Support Features**: Demonstrate post-booking capabilities

### Key Features to Highlight:
- 🤖 Seamless agent handoffs
- 📚 RAG accuracy with your PDF documents
- 💬 Context preservation across agents
- 🎨 Rich console interface
- ⚡ Real-time processing

### Console Commands to Show:
- `/services` - Display service catalog
- `/status` - Check booking status
- `/help` - Show capabilities

### Error Handling:
- Try misspellings to show robustness
- Ask ambiguous questions to show clarification
- Test edge cases like past dates for booking