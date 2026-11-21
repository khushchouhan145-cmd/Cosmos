type Props = {
  title: string;
  lesson: string;
};

export function ComingSoonPage({ title, lesson }: Props) {
  return (
    <main style={{ padding: "40px" }}>
      <p>{lesson}</p>
      <h1>{title}</h1>
      <p>This feature is coming soon. Continue learning COSMOS!</p>
    </main>
  );
}