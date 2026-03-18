# Understanding Lithium-Ion Battery Degradation: Causes, Effects, and Solutions

**Source:** https://www.zitara.com/resources/lithium-ion-battery-degradation

---

## A Primer on Lithium-Ion Batteries

Lithium-ion battery degradation is unavoidable—these batteries will degrade over time whether you use them or not, and they'll degrade even faster if you don't operate them properly. There are, however, steps you can take to help mitigate the effects of battery degradation.

A cell comprises two electrodes (the anode and the cathode), a porous separator between the electrodes, and electrolyte—a liquid (solvent) with special ions that wets the other components and facilitates transport of lithium ions between the electrodes. This movement of lithium ions is the workhorse principle of cell operation. A cell's inventory of lithium ions is finite, originating primarily from the cathode material and secondarily from lithium salts in the electrolyte.

**During charge:** Lithium ions move from the cathode, through the electrolyte, into the anode.

**During discharge:** Lithium ions move from the anode, through the electrolyte, into the cathode.

---

## Why Do Lithium-Ion Batteries Degrade?

Several internal phenomena cause degradation in a lithium-ion battery cell:

- Undesired reactions between the electrolyte solvent and/or salts, lithium ions, and/or electrode surfaces
- Physical changes to the active electrode materials, such as cracking and swelling
- Loss of electrical connection between lithium-containing active electrode material and the bulk electrode
- Side reactions between the electrolyte and current collectors

These mechanisms contribute to a reduction in a cell's performance and capacity.

---

## Six Common Causes of Lithium-Ion Battery Degradation

While lithium-ion battery degradation is unavoidable, the rate at which it occurs can vary significantly depending on operating conditions. Degradation will be fastest under extreme conditions such as high temperatures, high current rates, or cold temperatures with high charging current rates.

### Causes Due to Regular Use

#### 1. Calendar Aging

Lithium-ion batteries are constantly degrading—even when they're not in use—simply as a consequence of time and thermodynamics. This is called **calendar aging**, which results from unavoidable chemical side reactions that take place at all times.

The primary side reaction is the growth of the **solid electrolyte interphase (SEI)**. In the first charge cycle after cell assembly, SEI grows and acts as a passivating film on the anode, preventing uncontrolled reaction between the electrolyte and the anode. However, the SEI slowly grows throughout the battery's lifetime, which continues to consume the electrolyte and lithium ions. SEI growth is especially accelerated at elevated temperatures.

Thicker SEI increases cell internal resistance, which limits performance and can further accelerate side reactions due to more internal heating. Consumption of the cell's lithium ions through SEI growth is one contributing factor to **loss of lithium inventory (LLI)**.

Because these reactions occur even when the cell is not in use, lithium-ion battery degradation is unavoidable. There are, however, methods to slow calendar aging, such as storing cells at a low temperature and low state of charge.

#### 2. Cycling-Based Degradation

The cycle of charging and discharging plays a large role in lithium-ion battery degradation, since the act of charging and discharging accelerates SEI growth and LLI beyond the rate at which it would occur in a cell that only experiences calendar aging. This is called **cycling-based degradation**.

A battery completes a full cycle every time it is completely drained (to 0% capacity) and then completely recharged (to 100% capacity). A battery completes a partial cycle whenever it is charged and discharged short of its full capacity. The more full and partial cycles a battery completes, the more it degrades.

Many lithium-ion battery manufacturers rate their batteries according to cycling-based degradation. For example, a battery may be rated as being able to complete 1,000 full cycles before it degrades from full capacity to 80% capacity. Unfortunately, this single number fails to capture the full complexity and breadth of effects that degradation has on batteries and the systems that rely on them.

### Causes Due to Irregular Use

#### 3. Fast Charging

Though it may sound advantageous, fast charging contributes to accelerated lithium-ion battery degradation. If you charge a lithium-ion battery too fast, you risk **lithium plating**.

Lithium plating causes even more severe degradation than SEI. Like SEI formation, lithium plating consumes lithium inventory—but it does so much more rapidly.

During lithium plating, solid lithium metal forms on the anode. Because lithium is a very reactive and highly resistive compound, it participates in side reactions and increases internal resistance. This leads to not only LLI but also higher resistance and therefore weaker performance—initiating a snowballing cycle of degradation.

#### 4. Exposure to High Temperatures

High temperatures are always a cause for concern when it comes to lithium-ion batteries. Exposure to high temperatures causes batteries to degrade more quickly, diminishing their lifetime overall.

Exposing lithium-ion batteries to high temperatures has a twofold effect:

1. It accelerates the already unavoidable calendar aging.
2. It causes the battery to degrade faster during normal charge/discharge cycles.

High temperatures induce the electrolyte's chemical side reactions more quickly, furthering electrolyte degradation. Moreover, exposure to very high temperatures (above 60°C) can cause **transition-metal dissolution**, where transition metals migrate from the cathode to the anode. This accelerates side reactions such as SEI, causing further degradation.

#### 5. Overcharging and Overdischarging

Lithium-ion batteries further degrade if they are overcharged (charged past 100% capacity) or overdischarged (discharged below 0% capacity).

If current is pushed into a battery that's already fully charged, the battery may become damaged and experience a fire or other thermal event. This is one of many reasons why battery management systems (BMSs) are crucial for safe lithium-ion battery operation.

As with fast charging, overcharging a lithium-ion battery can result in lithium plating, which kicks off a rapid, snowball effect of degradation.

The anode can sometimes degrade more rapidly than the cathode. This upsets the battery's electrode capacity alignment, effectively altering the upper limit of the voltage safe operating area (SOA) and transforming what was once a safe cutoff voltage for charging into a voltage that overcharges your anode—thus stimulating further degradation.

To prevent lithium plating, take precautions to avoid overcharging in the first place.

#### 6. Physical Abuse

Besides considering charging cycles, charging rates, temperatures, and overcharging/discharging, it's also important to consider external factors. A battery that is physically dented, dinged, bent, crushed, pierced, or damaged in any way can experience extremely rapid degradation and even cause a hazardous situation.

---

## Four Effects and Consequences of Battery Degradation

Lithium-ion battery degradation reduces the overall lifespan of a battery, but what happens to the electrical properties when a battery starts to degrade?

### 1. Lower Capacity

One of the most well-known effects of a degraded battery is lowered capacity. After a couple of years, a degraded lithium-ion battery cannot store as much energy as it could when it was new.

**Real-world example:** Your phone, laptop, or other devices don't last as long after just a couple years of use.

### 2. Reduced Power Capability

Beyond reduced capacity, a degraded lithium-ion battery also suffers from **reduced power capability**—the battery absorbs and releases electrical energy at slower rates and less efficiently than before. This is due to increased internal resistance, which causes the degraded battery to generate more heat during operation.

Increased heat generation then causes the battery to wear out faster, sparking a cycle of degradation.

**Real-world example:** EVs with a degraded battery charge, accelerate, and regeneratively brake more slowly.

### 3. Degraded Controls

As a lithium-ion battery degrades and operates with less efficiency, BMS controls may also deteriorate. Off-the-shelf software onboard today's BMSs are often programmed to treat a battery as if it were new—despite the fact that degraded batteries behave very differently from new ones. This means existing BMSs will be operating with inaccurate information—increasingly so as degradation worsens.

As a result, the consequences of a degraded lithium-ion battery can extend far beyond a shorter battery life and excessive heat generation.

### 4. Battery Swelling

Side reactions at high temperatures can generate gases which result in a swollen battery. These gases pressurize and build resistive pockets in the battery, rapidly degrading performance and lifespan.

While battery swelling can occur in any kind of battery cell, it's more likely to be observed in pouch cells since they lack a rigid structure.

**Real-world impact:** Excessive battery swelling poses a serious safety risk; any devices with swollen batteries should not be used, and the batteries should be immediately replaced.

---

## Methods to Mitigate and Measure Battery Degradation

Inevitably, lithium-ion batteries will degrade. There's no way around it. Even if you practice safe operations and never abuse your batteries, they will always degrade due to cycling and calendar aging.

You can, however, take action to delay lithium-ion battery degradation and mitigate its effects, and you can measure and track battery degradation to best prepare your battery fleet for long-term success.

### How to Mitigate Battery Degradation

#### 1. Design Around It

The first step you can take to mitigate battery degradation is to design around it.

For example, suppose your battery system needs to deliver 80 Wh of energy at the end of its lifetime. Since battery degradation is unavoidable and your battery system will not operate at 100% capacity forever, you can design with 80% capacity in mind.

This means designing your battery system with a significantly larger capacity than necessary so that it still has sufficient capacity at the end of its life. In this example, you would design your battery system to be capable of delivering 100 Wh (80 Wh + 20 Wh) of energy at the beginning of its lifespan, with 20 Wh representing the predicted capacity loss due to future degradation. This way, even at the end of its life, your battery system will still deliver the 80 Wh of energy needed.

#### 2. Manage Temperature

High temperatures play a significant role in contributing to battery degradation. While events like improper fast charging and overcharging can cause exposure to high temperature, the battery's external environment can also be the culprit.

A properly designed thermal management system can minimize the rate of battery degradation. To determine what type of thermal management system may be necessary for your application, first consider the environment and the typical use cases of your battery system. Air-, liquid-, and refrigerant-based thermal management systems are all common methods of regulating battery temperature.

#### 3. Use Degradation-Resilient Controls

While you cannot entirely prevent lithium-ion battery degradation, you can minimize its effect on the performance of your controls.

For example, model-based algorithms with an accurate degradation model can enable a BMS to monitor battery degradation in the field and adapt accordingly. This empowers users and system owners to continuously adjust battery usage patterns to minimize future degradation, resulting in more consistent and reliable battery operation.

### How Today's Degradation Metrics Are Falling Short

Often the complexities of battery degradation get boiled down into simple metrics—**State of Health (SoH)**—which typically combines capacity and resistance measurements:

#### 1. Capacity Measurement

Battery manufacturers analyze capacity changes over time to get a rough estimate of degradation. SoH is often provided as a percentage of the battery's original capacity and is used for warranties and performance guarantees.

However, while easy to measure and understand, a capacity-only metric fails to describe the many internal effects that cause degradation. It can provide only limited value for understanding and predicting how a battery will function in real-world applications.

#### 2. Resistance Measurement

Similarly, manufacturers can measure internal resistance fairly easily by looking at the short-term voltage response to load changes.

Since internal resistance increases as a battery degrades, manufacturers can make a simple comparison to the initial resistance to estimate the SoH. But again, this metric fails to capture the nuances of all the internal changes that cause degradation and falls short of being comprehensive in understanding and predicting how a battery will function in the field.

### How to Manage Battery Degradation

While measuring battery capacity and resistance can be helpful indicators about a battery's degradation, these indicators lack precision and reliability.

To best manage your batteries for long-term success, look instead for ways to gain more actionable insights, allowing you to pinpoint opportunities to reduce battery degradation and increase the lifespan of your fleet.

---

## Advanced Degradation Monitoring and Prediction

One way to keep track of batteries and manage their degradation is with advanced, model-based predictive algorithms and cloud-ready battery management software that works across battery chemistries.

### What This Approach Offers

Advanced predictive algorithms help you stay ahead by tracking the degradation of your batteries and giving you actionable insights into how that degradation is affecting performance.

Typical battery management systems are unable to anticipate your battery fleet's projected energy availability. When it comes to monitoring safety, they can't deliver much beyond simple limits on temperature, voltage, and current.

Model-based algorithms are continuously learning. Using precise onboard simulations, they can predict the energy, power, and heat generation of your batteries now and into the future—with granularity that takes into account the entire seen and unseen state of a battery. This provides:

- A complete bird's-eye view of all your batteries
- Comprehensive degradation tracking and performance predictions
- Accurate degradation estimation enabling actionable insights
- The ability to adjust battery usage patterns to minimize future degradation

This information is essential for real-world applications, as batteries are often the most expensive (and unpredictable) parts of your operation. By integrating advanced algorithms with your system, you can unlock powerful insights about your batteries' degradation so you can plan for the long term and boost operations.

---

## Lithium-Ion Battery Degradation FAQs

### How long does it take lithium-ion batteries to degrade?

Lithium-ion batteries begin degrading immediately upon use. However, no two batteries degrade at exactly the same rate. Rather, their degradation varies depending on operating conditions. In general, most lithium-ion batteries will degrade to 80% of their full capacity between 500 and 2,000 cycles.

### Do lithium-ion batteries degrade if not used?

Unfortunately, yes—lithium-ion batteries will still degrade even if not in use. This is called **calendar aging**, where the battery degrades as a function of time. Calendar aging is unavoidable because the degradation occurs even when there is zero battery usage.

### What happens when a lithium battery degrades?

When a lithium battery degrades, end users will notice:

- **Lower capacity:** The battery will die faster than it did when new
- **Reduced power capability:** The battery will charge more slowly than it did when brand new from the manufacturer
