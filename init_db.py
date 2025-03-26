from app import app, db, Agent, DailyPerformance
from datetime import datetime, timedelta
import random
import os

def create_sample_data():
    with app.app_context():
        # Drop all tables and recreate them
        db.drop_all()
        db.create_all()

        # Actual agent data
        agents_data = [
            # Austin Training Agents
            {"name": "Dawn Dawson", "division": "Austin Call Center", "manager": "Mario Herrera", "queue_type": "Training"},
            {"name": "Tim Dominguez", "division": "Austin Call Center", "manager": "David Druxman", "queue_type": "Training"},
            {"name": "Brandon Escort", "division": "Austin Call Center", "manager": "Patricia Lewis", "queue_type": "Training"},
            {"name": "Katherine Freeman", "division": "Austin Call Center", "manager": "Patricia Lewis", "queue_type": "Training"},
            {"name": "Celeste Garcia", "division": "Austin Call Center", "manager": "Patricia Lewis", "queue_type": "Training"},
            {"name": "Jeff Korioth", "division": "Austin Call Center", "manager": "Lanae Edwards", "queue_type": "Training"},
            {"name": "Crystal Kurtanic", "division": "Austin Call Center", "manager": "Mario Herrera", "queue_type": "Training"},
            {"name": "Nikia Lewis", "division": "Austin Call Center", "manager": "Frederick Holguin", "queue_type": "Training"},
            {"name": "Drew Lombard", "division": "Austin Call Center", "manager": "David Druxman", "queue_type": "Training"},
            {"name": "Cynthia Mbaka", "division": "Austin Call Center", "manager": "Patricia Lewis", "queue_type": "Training"},
            {"name": "Andy Nickleson", "division": "Austin Call Center", "manager": "Frederick Holguin", "queue_type": "Training"},
            {"name": "Pedro Rodrigues", "division": "Austin Call Center", "manager": "Lanae Edwards", "queue_type": "Training"},
            {"name": "Rose Scales", "division": "Austin Call Center", "manager": "Lanae Edwards", "queue_type": "Training"},

            # Charlotte Training Agents
            {"name": "Alexis Alexander", "division": "Charlotte Call Center", "manager": "Jamal Gipson", "queue_type": "Training"},
            {"name": "Gerard Apadula", "division": "Charlotte Call Center", "manager": "Brent Lahti", "queue_type": "Training"},
            {"name": "Wenny Gooding", "division": "Charlotte Call Center", "manager": "Jacob Fuller", "queue_type": "Training"},
            {"name": "Quincy Jones", "division": "Charlotte Call Center", "manager": "Brent Lahti", "queue_type": "Training"},
            {"name": "Don Mccoy", "division": "Charlotte Call Center", "manager": "Brent Lahti", "queue_type": "Training"},
            {"name": "Montrell Morgan", "division": "Charlotte Call Center", "manager": "Jovan Espinoza", "queue_type": "Training"},
            {"name": "Jeffrey Rosenberg", "division": "Charlotte Call Center", "manager": "Jacob Fuller", "queue_type": "Training"},
            {"name": "Niko Smallwood", "division": "Charlotte Call Center", "manager": "Nisrin Hajmahmoud", "queue_type": "Training"},
            {"name": "Dawn Strong", "division": "Charlotte Call Center", "manager": "Jamal Gipson", "queue_type": "Training"},
            {"name": "Chris Williams", "division": "Charlotte Call Center", "manager": "Brent Lahti", "queue_type": "Training"},
            {"name": "Priscille Wembo", "division": "Charlotte Call Center", "manager": "Brent Lahti", "queue_type": "Training"},

            # Austin Performance Agents
            {"name": "Iesha Alexander", "division": "Austin Call Center", "manager": "David Druxman", "queue_type": "Performance"},
            {"name": "Jremekyo Anderson", "division": "Austin Call Center", "manager": "David Druxman", "queue_type": "Performance"},
            {"name": "Jack Benken", "division": "Austin Call Center", "manager": "Lanae Edwards", "queue_type": "Performance"},
            {"name": "Micah Black", "division": "Austin Call Center", "manager": "Frederick Holguin", "queue_type": "Performance"},
            {"name": "Michelle Brown", "division": "Austin Call Center", "manager": "Mario Herrera", "queue_type": "Performance"},
            {"name": "Leif Carlson", "division": "Austin Call Center", "manager": "Patricia Lewis", "queue_type": "Performance"},
            {"name": "Rachel Choate", "division": "Austin Call Center", "manager": "Lanae Edwards", "queue_type": "Performance"},
            {"name": "Doug Curttright", "division": "Austin Call Center", "manager": "Frederick Holguin", "queue_type": "Performance"},
            {"name": "Mark Garcia", "division": "Austin Call Center", "manager": "Mario Herrera", "queue_type": "Performance"},
            {"name": "Amber Hartwick", "division": "Austin Call Center", "manager": "Mario Herrera", "queue_type": "Performance"},
            {"name": "Justin Hinze", "division": "Austin Call Center", "manager": "Mario Herrera", "queue_type": "Performance"},
            {"name": "Jovon Holts", "division": "Austin Call Center", "manager": "Patricia Lewis", "queue_type": "Performance"},
            {"name": "Austin Houser", "division": "Austin Call Center", "manager": "Frederick Holguin", "queue_type": "Performance"},
            {"name": "Magifira Jemal", "division": "Austin Call Center", "manager": "Lanae Edwards", "queue_type": "Performance"},
            {"name": "William Knight", "division": "Austin Call Center", "manager": "Patricia Lewis", "queue_type": "Performance"},
            {"name": "Eric Marrs", "division": "Austin Call Center", "manager": "Frederick Holguin", "queue_type": "Performance"},
            {"name": "Jonathon Mejia", "division": "Austin Call Center", "manager": "Patricia Lewis", "queue_type": "Performance"},
            {"name": "Alicia O'Bryant", "division": "Austin Call Center", "manager": "David Druxman", "queue_type": "Performance"},
            {"name": "Duncan Ordenana", "division": "Austin Call Center", "manager": "Lanae Edwards", "queue_type": "Performance"},
            {"name": "Diana Roe", "division": "Austin Call Center", "manager": "Mario Herrera", "queue_type": "Performance"},
            {"name": "Ron Rydzfski", "division": "Austin Call Center", "manager": "Frederick Holguin", "queue_type": "Performance"},
            {"name": "John Sivy", "division": "Austin Call Center", "manager": "Frederick Holguin", "queue_type": "Performance"},
            {"name": "Billy Slater", "division": "Austin Call Center", "manager": "David Druxman", "queue_type": "Performance"},
            {"name": "Amy Slusarski", "division": "Austin Call Center", "manager": "Lanae Edwards", "queue_type": "Performance"},
            {"name": "Kierra Smith", "division": "Austin Call Center", "manager": "David Druxman", "queue_type": "Performance"},
            {"name": "Jaime Valdez", "division": "Austin Call Center", "manager": "Mario Herrera", "queue_type": "Performance"},
            {"name": "Roza Veravillalba", "division": "Austin Call Center", "manager": "Mario Herrera", "queue_type": "Performance"},

            # Charlotte Performance Agents
            {"name": "Camryn Anderson", "division": "Charlotte Call Center", "manager": "Nisrin Hajmahmoud", "queue_type": "Performance"},
            {"name": "Kb Bolar", "division": "Charlotte Call Center", "manager": "Katelyn Helms", "queue_type": "Performance"},
            {"name": "Kenya Caldwell", "division": "Charlotte Call Center", "manager": "Jovan Espinoza", "queue_type": "Performance"},
            {"name": "Beau Carson", "division": "Charlotte Call Center", "manager": "Katelyn Helms", "queue_type": "Performance"},
            {"name": "Robert Carter", "division": "Charlotte Call Center", "manager": "Jovan Espinoza", "queue_type": "Performance"},
            {"name": "Hunter Case", "division": "Charlotte Call Center", "manager": "Jovan Espinoza", "queue_type": "Performance"},
            {"name": "Chris Chen", "division": "Charlotte Call Center", "manager": "Nisrin Hajmahmoud", "queue_type": "Performance"},
            {"name": "Joe Coleman", "division": "Charlotte Call Center", "manager": "Jacob Fuller", "queue_type": "Performance"},
            {"name": "Serena Cowan", "division": "Charlotte Call Center", "manager": "Nisrin Hajmahmoud", "queue_type": "Performance"},
            {"name": "Alvin Fulmore", "division": "Charlotte Call Center", "manager": "Jamal Gipson", "queue_type": "Performance"},
            {"name": "Loren Johnson", "division": "Charlotte Call Center", "manager": "Jamal Gipson", "queue_type": "Performance"},
            {"name": "Kevin Gray", "division": "Charlotte Call Center", "manager": "Jamal Gipson", "queue_type": "Performance"},
            {"name": "Gee Grayer", "division": "Charlotte Call Center", "manager": "Vincent Blanchett", "queue_type": "Performance"},
            {"name": "Adelina Guardado", "division": "Charlotte Call Center", "manager": "Vincent Blanchett", "queue_type": "Performance"},
            {"name": "Arlethe Guevara", "division": "Charlotte Call Center", "manager": "Katelyn Helms", "queue_type": "Performance"},
            {"name": "Lynethe Guevara", "division": "Charlotte Call Center", "manager": "Vincent Blanchett", "queue_type": "Performance"},
            {"name": "Dustin Gunter", "division": "Charlotte Call Center", "manager": "Nisrin Hajmahmoud", "queue_type": "Performance"},
            {"name": "DeAngela Harris", "division": "Charlotte Call Center", "manager": "Vincent Blanchett", "queue_type": "Performance"},
            {"name": "Johnathan Hubbard", "division": "Charlotte Call Center", "manager": "Jamal Gipson", "queue_type": "Performance"},
            {"name": "Tyler Jacobson", "division": "Charlotte Call Center", "manager": "Katelyn Helms", "queue_type": "Performance"},
            {"name": "Damien King", "division": "Charlotte Call Center", "manager": "Jamal Gipson", "queue_type": "Performance"},
            {"name": "DaVon Loney", "division": "Charlotte Call Center", "manager": "Jamal Gipson", "queue_type": "Performance"},
            {"name": "Kenny Mclaughlin", "division": "Charlotte Call Center", "manager": "Jovan Espinoza", "queue_type": "Performance"},
            {"name": "Quinn Mcleod", "division": "Charlotte Call Center", "manager": "Jacob Fuller", "queue_type": "Performance"},
            {"name": "Peter Nguyen", "division": "Charlotte Call Center", "manager": "Jovan Espinoza", "queue_type": "Performance"},
            {"name": "Damond Outing", "division": "Charlotte Call Center", "manager": "Jovan Espinoza", "queue_type": "Performance"},
            {"name": "Keviantae Paul", "division": "Charlotte Call Center", "manager": "Katelyn Helms", "queue_type": "Performance"},
            {"name": "Mitchell Pitman", "division": "Charlotte Call Center", "manager": "Vincent Blanchett", "queue_type": "Performance"},
            {"name": "Miguel Roman", "division": "Charlotte Call Center", "manager": "Jacob Fuller", "queue_type": "Performance"},
            {"name": "Jimmie Royster", "division": "Charlotte Call Center", "manager": "Nisrin Hajmahmoud", "queue_type": "Performance"},
            {"name": "Lexi Salinas", "division": "Charlotte Call Center", "manager": "Katelyn Helms", "queue_type": "Performance"},
            {"name": "Cameran Sanders", "division": "Charlotte Call Center", "manager": "Jacob Fuller", "queue_type": "Performance"},
            {"name": "Dennis Smith", "division": "Charlotte Call Center", "manager": "Jacob Fuller", "queue_type": "Performance"},
            {"name": "Gabrielle Smith", "division": "Charlotte Call Center", "manager": "Vincent Blanchett", "queue_type": "Performance"},
            {"name": "Jahne Spears", "division": "Charlotte Call Center", "manager": "Nisrin Hajmahmoud", "queue_type": "Performance"},
            {"name": "Vannak Suos", "division": "Charlotte Call Center", "manager": "Vincent Blanchett", "queue_type": "Performance"},
            {"name": "Asaad Weaver", "division": "Charlotte Call Center", "manager": "Katelyn Helms", "queue_type": "Performance"},
            {"name": "Kyle Williford", "division": "Charlotte Call Center", "manager": "Katelyn Helms", "queue_type": "Performance"},
            {"name": "Douglas Yang", "division": "Charlotte Call Center", "manager": "Vincent Blanchett", "queue_type": "Performance"}
        ]

        # Create agents
        agents = []
        for agent_data in agents_data:
            agent = Agent(
                name=agent_data["name"],
                division=agent_data["division"],
                manager=agent_data["manager"],
                queue_type=agent_data["queue_type"]
            )
            db.session.add(agent)
            agents.append(agent)
        
        db.session.commit()

        # Generate 30 days of performance data for each agent
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)
        current_date = start_date

        while current_date <= end_date:
            for agent in agents:
                # Generate realistic performance data based on queue type
                if agent.queue_type == 'Training':
                    close_rate = random.uniform(12, 18)
                    place_rate = random.uniform(55, 65)
                    avg_premium = random.uniform(900, 1200)
                else:
                    close_rate = random.uniform(17, 25)
                    place_rate = random.uniform(60, 70)
                    avg_premium = random.uniform(1000, 1300)

                performance = DailyPerformance(
                    date=current_date,
                    agent_id=agent.id,
                    leads_taken=random.uniform(6, 9),
                    close_rate=close_rate,
                    place_rate=place_rate,
                    avg_premium=avg_premium,
                    talk_time_minutes=random.randint(120, 240),
                    notes=f'Sample data for {current_date}'
                )

                # Calculate and set derived fields
                performance.placed_premium_per_lead = performance.calculate_ppl()
                performance.total_daily_premium = performance.calculate_daily_premium()
                
                db.session.add(performance)
            
            current_date += timedelta(days=1)
        
        db.session.commit()

if __name__ == '__main__':
    create_sample_data() 